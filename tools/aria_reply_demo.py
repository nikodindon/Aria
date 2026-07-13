"""
tools/aria_reply_demo.py — Demonstration end-to-end du pipeline ARIA.

Sequence :
  1. Reset vers la vue Discussions (press_back).
  2. list_conversations() : trouve la conv avec le num specifie.
  3. open_conversation() : ouvre la conv.
  4. read_conversation() : lit les messages.
  5. brain.chat() : genere une reponse via LLM avec system prompt ARIA.
  6. send_message(phone=...) : envoie la reponse via deep link.

C'est la demonstration que ARIA peut lire un message WhatsApp entrant,
generer une reponse contextuelle, et l'envoyer. Pas un test unitaire,
une demonstration manuelle qu'on lance quand on veut voir le pipeline
tourner.

Usage :
  python tools/aria_reply_demo.py
  python tools/aria_reply_demo.py --phone 33617186267
"""
import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import adb
from bridge.whatsapp import (
    current_view, list_conversations, open_conversation,
    read_conversation, send_message,
)
from core.brain import chat
from core.context_builder import SYSTEM_PERSONA
from core.personality import format_mood_for_prompt


def find_user_conversation(phone_digits: str):
    """Trouve la conversation avec le num donne dans la liste."""
    convs = list_conversations()
    # Le num apparait dans le nom affiche, avec espaces et +
    for c in convs:
        name_digits = "".join(ch for ch in c["name"] if ch.isdigit())
        if name_digits.endswith(phone_digits[-9:]):  # match les 9 derniers chiffres
            return c
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", default="33617186267",
                        help="Numero du contact au format international (defaut: 33617186267)")
    parser.add_argument("--max-tokens", type=int, default=300)
    args = parser.parse_args()

    print(f"=== ARIA end-to-end demo ===")
    print(f"phone: {args.phone}")
    print(f"max_tokens: {args.max_tokens}")
    print()

    # 1. Reset vers Discussions
    if current_view() == "conversation":
        print("[1/6] Retour a Discussions...")
        adb.press_back()
        time.sleep(0.5)
    print(f"      current_view = {current_view()}")
    print()

    # 2. Trouver la conv
    print("[2/6] Recherche de la conversation...")
    conv = find_user_conversation(args.phone)
    if not conv:
        print(f"      ERREUR: pas de conversation trouvee pour le num {args.phone}")
        print(f"      Liste actuelle : {[c['name'] for c in list_conversations()]}")
        return 1
    print(f"      Trouvee : {conv['name']!r} (badge={conv['badge']})")
    print()

    # 3. Ouvrir
    print("[3/6] Ouverture de la conversation...")
    if not open_conversation(conv["name"]):
        print("      ERREUR: open_conversation a echoue")
        return 1
    time.sleep(1.0)
    print()

    # 4. Lire
    print("[4/6] Lecture des messages...")
    msgs = read_conversation()
    last_in = None
    for m in reversed(msgs):
        if m["direction"] == "in" and m["text"].strip():
            last_in = m["text"]
            break
    if not last_in:
        print("      ERREUR: aucun message entrant trouve")
        return 1
    print(f"      Dernier message entrant : {last_in[:80]!r}")
    print()

    # 5. Generer reponse
    print("[5/6] Generation de la reponse via LLM...")
    mood = format_mood_for_prompt()
    system = SYSTEM_PERSONA.format(
        context="Conversation WhatsApp. Niko vient de t'ecrire.",
        mood_state=mood,
    )
    user_msg = (
        f"Niko vient de t'envoyer ce message WhatsApp :\n\n{last_in}\n\n"
        "Reponds en 2-3 phrases max, comme une vraie conversation WhatsApp. "
        "Sois naturelle, pas de formule de politesse chiante. "
        "Pas de mensonges sur ce que tu fais (ne pretend pas avoir lu des trucs "
        "si c'est faux)."
    )
    response = chat(
        messages=[{"role": "user", "content": user_msg}],
        system=system,
        max_tokens=args.max_tokens,
    )
    print(f"      Reponse generee : {response!r}")
    print()

    # 6. Envoyer
    print("[6/6] Envoi via deep link...")
    result = send_message(response, phone=args.phone)
    print(f"      send_message : {result}")
    print()
    print("=== Done. Verifie sur ton telephone perso que la reponse est bien arrivee. ===")
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
