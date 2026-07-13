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

    Utilise build_whatsapp_context() qui assemble le system prompt
    (persona + mood) ET injecte les 15 derniers messages de la DB
    dans le prompt user. C'est la memoire court-terme.
    """
    sender = user.get("name") or user["phone"]
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

    # 2. Envoi via deep link
    try:
        send_message(response, phone=user["phone"])
    except Exception as e:
        print(f"[aria_loop] send failed: {e}")
        return False

    # 3. Log en DB (in + out)
    log_message("whatsapp", sender, "in", last_message)
    log_message("whatsapp", "ARIA", "out", response)
    touch_user(user["id"])

    # 4. Mood update : derive le mood de la longueur et du ton de
    # l'echange. KISS : on prend la longueur de la reponse comme
    # proxy d'engagement, et on incremente curiosity si l'incoming
    # contenait un point d'interrogation.
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
        print(f"[aria_loop] nouvelle notif de {user.get('name') or phone}: {n['text'][:60]!r}")
        if reply_to_user(user, n["text"]):
            treated += 1
    return treated


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
