"""
tools/aria_loop.py — Boucle gateway ARIA (Phase 2).

Poll `dumpsys notification` toutes les N secondes, detecte les
nouveaux messages WhatsApp, et dispatche :

  - Si l'expediteur est un user appaire (table `users`) :
      - Lit le message complet (deep link + UI Automator)
      - Genere une reponse via LLM
      - Envoie via deep link
      - Log en DB

  - Sinon :
      - Ignore (ou repond avec un message de refus si on veut)

C'est la version simplifiee du gateway Hermes-style. Pas d'API
cloud, pas de Twilio, pas de cle. Tout passe par ADB + WhatsApp
local sur le telephone dedie.

Usage :
  python tools/aria_loop.py                    # poll toutes les 30s
  python tools/aria_loop.py --interval 10      # poll toutes les 10s
  python tools/aria_loop.py --once             # une seule iteration

Limitations actuelles :
  * On matche le num dans dumpsys via android.title (qui contient
    le nom du contact ou le num). Pas toujours fiable.
  * Le pipeline de reponse (deep link + read + LLM + send) prend
    ~5-10s par message. Donc interval doit etre >= 15s en pratique.
  * Pas de gestion d'erreur avancee : si un tap rate, on log et
    on continue.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.brain import chat
from core.context_builder import build_whatsapp_context
from core.memory import (
    get_user_by_phone, list_users, log_message, touch_user, save_mood,
    get_recent_messages,
)
from bridge import adb
from bridge.whatsapp import (
    current_view, list_conversations, open_conversation,
    read_conversation, send_message,
)
import re as _re


def dump_notifications() -> str:
    """Retourne le contenu de dumpsys notification."""
    result = adb._adb("shell", "dumpsys", "notification", "--noredact", check=True)
    return result


def parse_whatsapp_notifications(dump: str) -> list[dict]:
    """Parse les notifs WhatsApp, retourne une liste de notifs.

    Chaque notif extraite : {title (avec num/nom), text (apercu),
    package (com.whatsapp), key (unique).}

    On ne s'interesse qu'aux notifs de com.whatsapp.
    """
    notifs = []
    # Split par pkg= et garde ceux de whatsapp
    chunks = dump.split("pkg=")
    for chunk in chunks:
        if not chunk.startswith("com.whatsapp"):
            continue
        # Extrait le title (numero ou nom de contact)
        title_m = _re.search(r"android\.title=String \(([^)]+)\)", chunk)
        text_m = _re.search(r"android\.text=String \(([^)]+)\)", chunk)
        key_m = _re.search(r"key=([^\s]+)", chunk)
        if not (title_m and key_m):
            continue
        # Le title est souvent "WhatsApp : +33 6 17 18 62 67" ou
        # "WhatsApp : Nom du contact". On extrait apres "WhatsApp : "
        title = title_m.group(1)
        text = text_m.group(1) if text_m else ""
        notifs.append({
            "title": title,
            "text": text,
            "key": key_m.group(1),
        })
    return notifs


def extract_phone_from_title(title: str) -> str | None:
    """Extrait un num de telephone d'un title de notif WhatsApp.

    Heuristique : cherche une sequence de chiffres avec espaces
    type '+33 6 17 18 62 67' ou '+33617186267'. Si pas de num,
    c'est un nom de contact (auquel cas on matchera par nom).
    """
    # Pattern international avec espaces : +XX X XX XX XX XX
    m = _re.search(r"\+(\d{1,3})\s*(\d[\s\d]{6,})", title)
    if m:
        digits = m.group(1) + _re.sub(r"\s+", "", m.group(2))
        return digits
    # Pattern national : 0X XX XX XX XX
    m = _re.search(r"\b0(\d[\s\d]{7,})\b", title)
    if m:
        digits = "0" + _re.sub(r"\s+", "", m.group(1))
        return digits
    return None


def reply_to_user(user: dict, last_message: str) -> bool:
    """Genere une reponse via LLM et l'envoie a l'user via deep link.

    Strategie :
    1. Detecte si le message necessite une recherche web (keywords)
    2. Si oui, delegue a un agent helper (hermes) qui fait la recherche
    3. Sinon, utilise le LLM local (M2.7-7b) avec le contexte complet

    Dans les 2 cas, on log en DB (in + out) et on update le mood.
    """
    sender = user.get("name") or user["phone"]
    response = None

    # 1. Detection de besoin de delegation
    from plugins.agent_delegate import delegate_for_message
    delegated = delegate_for_message(last_message)
    if delegated is not None:
        print(f"[aria_loop] delegation a un agent helper (keywords trouves)")
        response = delegated
    else:
        # 2. Sinon, LLM local avec contexte complet
        try:
            system, messages = build_whatsapp_context(sender, last_message)
        except Exception as e:
            print(f"[aria_loop] build_context failed: {e}")
            return False

        try:
            response = chat(
                messages=messages,
                system=system,
                max_tokens=300,
            )
        except Exception as e:
            print(f"[aria_loop] LLM failed: {e}")
            return False

    # 3. Envoi via deep link
    try:
        send_message(response, phone=user["phone"])
    except Exception as e:
        print(f"[aria_loop] send failed: {e}")
        return False

    # 4. Log en DB (in + out)
    log_message("whatsapp", sender, "in", last_message)
    log_message("whatsapp", "ARIA", "out", response)
    touch_user(user["id"])

    # 5. Mood update
    update_mood_from_interaction(last_message, response)

    return True


def update_mood_from_interaction(incoming: str, outgoing: str):
    """Ajuste le mood d'ARIA en fonction de l'interaction.

    Heuristique KISS :
    - Si l'incoming contient '?' => curiosity monte
    - Si outgoing > 200 chars => engagement haut
    - Sinon mood neutre
    """
    from core.memory import get_current_mood
    current = get_current_mood()
    curiosity = current.get("curiosity", "normale")
    energy = current.get("energy", "normale")
    if "?" in incoming:
        curiosity = "élevée"
    if len(outgoing) > 200:
        energy = "haute"
    elif len(outgoing) < 50:
        energy = "basse"
    save_mood(
        mood=current.get("mood", "neutre"),
        energy=energy,
        curiosity=curiosity,
        reason=f"interaction ({len(incoming)}c in, {len(outgoing)}c out)",
    )


def process_pending_notifications(seen_keys: set) -> int:
    """Traite les notifs WhatsApp pas encore vues. Retourne le nombre traite.

    Strategie de dedup : on stocke les cles du poll PRECEDENT dans
    `seen_keys`. Une notif est "nouvelle" si elle est dans le poll
    actuel ET PAS dans `seen_keys`. Apres traitement, on met a jour
    `seen_keys` avec les cles du poll actuel.

    Pourquoi ne pas utiliser directement seen_keys comme dedup global ?
    Parce qu'Android peut reemettre la meme notif avec la meme cle
    dans des dumps successifs tant qu'elle n'est pas dismissed par
    l'utilisateur. Vu qu'on les diff avec le poll precedent, une
    notif dejà vue n'est consideree nouvelle qu'une seule fois.

    Dedup temporel : en plus de la cle de notif, on dedup aussi sur
    le contenu texte. Si on a deja repondu a un message tres similaire
    (meme texte normalise) dans les DEDUP_WINDOW_MINUTES dernieres
    minutes, on skip. Ca protege contre les cas ou Android reemet
    la notif avec une cle differente (ex: apres rotation, ou apres
    que la notif originale a ete dismissed puis re-emise).
    """
    try:
        dump = dump_notifications()
    except Exception as e:
        print(f"[aria_loop] dumpsys failed: {e}")
        return 0

    notifs = parse_whatsapp_notifications(dump)
    current_keys = {n["key"] for n in notifs}
    new_keys = current_keys - seen_keys
    seen_keys.update(current_keys)

    # Charge l'historique des messages recemment traites (dedup temporel)
    recent_texts = _load_recent_texts(window_min=DEDUP_WINDOW_MINUTES)

    treated = 0
    for n in notifs:
        if n["key"] not in new_keys:
            continue
        phone = extract_phone_from_title(n["title"])
        if not phone:
            print(f"[aria_loop] notif sans num detecte: {n['title']!r}")
            continue
        user = get_user_by_phone(phone)
        if not user:
            print(f"[aria_loop] notif d'un num non appaire: {phone} ({n['title']!r})")
            continue
        # Dedup temporel : meme contenu dans les dernieres X min ?
        text_norm = _normalize_for_dedup(n["text"])
        if text_norm in recent_texts:
            print(f"[aria_loop] doublon recent detecte (meme texte en <{DEDUP_WINDOW_MINUTES}min), skip: {n['text'][:50]!r}")
            continue
        print(f"[aria_loop] nouvelle notif de {user.get('name') or phone}: {n['text'][:60]!r}")
        if reply_to_user(user, n["text"]):
            treated += 1
            # Enregistre le texte pour le dedup futur
            _record_text_seen(text_norm)
    return treated


DEDUP_WINDOW_MINUTES = 10
SEEN_TEXTS_PATH = Path("data/seen_texts.json")


def _normalize_for_dedup(text: str) -> str:
    """Normalise un texte pour dedup : lowercase, strip, retire ponctuation.

    'Comment tu vas ?' et 'comment tu vas' et 'Comment tu vas?' sont
    consideres identiques. On garde les accents (le redact_credentials
    peut etre different entre 2 messages similaires).
    """
    import re as _re
    t = text.lower().strip()
    # Retire ponctuation a la fin
    t = _re.sub(r"[\?\.\!\s]+$", "", t)
    return t


def _load_recent_texts(window_min: int = DEDUP_WINDOW_MINUTES) -> set[str]:
    """Charge les textes normalises vus recemment (moins de window_min)."""
    if not SEEN_TEXTS_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_TEXTS_PATH.read_text())
    except Exception:
        return set()
    now = time.time()
    cutoff = now - window_min * 60
    return {text for text, ts in data.items() if ts > cutoff}


def _record_text_seen(text_norm: str) -> None:
    """Enregistre un texte normalise comme vu maintenant. Persistant."""
    SEEN_TEXTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SEEN_TEXTS_PATH.exists():
        try:
            data = json.loads(SEEN_TEXTS_PATH.read_text())
        except Exception:
            data = {}
    else:
        data = {}
    # Nettoie les vieux (>DEDUP_WINDOW_MINUTES) avant d'ajouter
    now = time.time()
    cutoff = now - DEDUP_WINDOW_MINUTES * 60
    data = {t: ts for t, ts in data.items() if ts > cutoff}
    data[text_norm] = now
    SEEN_TEXTS_PATH.write_text(json.dumps(data))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=30, help="Secondes entre chaque poll")
    parser.add_argument("--once", action="store_true", help="Une seule iteration puis exit")
    args = parser.parse_args()

    users = list_users()
    if not users:
        print("Aucun user appaire. Lance d'abord :")
        print("  python tools/aria_pair.py --phone 33617186267 --name Niko")
        return 1
    print(f"=== ARIA loop gateway ===")
    print(f"Users apparies : {[u.get('name') or u['phone'] for u in users]}")
    print(f"Interval : {args.interval}s ({'once' if args.once else 'infini'})")
    print()

    seen_keys = set()
    try:
        while True:
            treated = process_pending_notifications(seen_keys)
            if treated:
                print(f"  -> {treated} message(s) traite(s)")
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[aria_loop] stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
