"""Tache : ARIA prend l'initiative de t'ecrire si trop de silence."""
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.brain import chat
from core.context_builder import SYSTEM_PERSONA
from core.memory import (
    get_recent_messages, list_users, log_message, touch_user,
)
from core.personality import format_mood_for_prompt
from bridge.whatsapp import send_message
from dotenv import load_dotenv

load_dotenv()

SILENCE_HOURS = int(os.getenv("PROACTIVE_SILENCE_HOURS", 48))


def run():
    """Si on n'a pas parle a un user depuis > SILENCE_HOURS, ARIA
    prend l'initiative et envoie un message spontane.

    Logique :
    1. Pour chaque user appaire
    2. Calcule le temps depuis le dernier message (echanges)
    3. Si > SILENCE_HOURS, genere un message spontane et envoie
    """
    users = list_users()
    if not users:
        return
    msgs = get_recent_messages(platform="whatsapp", limit=200)

    for user in users:
        # Trouve le dernier message avec ce user (sender = name ou phone)
        last_user_ts = None
        for m in msgs:
            if m["sender"] == user.get("name") or m["sender"] == user["phone"]:
                last_user_ts = m["ts"]
                break
        if not last_user_ts:
            # Pas de conversation avec ce user, on l'ignore
            continue
        last_dt = datetime.fromisoformat(last_user_ts)
        silence = datetime.now() - last_dt
        if silence < timedelta(hours=SILENCE_HOURS):
            continue

        print(f"[task:proactive_ping] {silence.days}j de silence avec "
              f"{user.get('name') or user['phone']} — ARIA prend l'initiative.")

        # Genere un message spontane
        mood_str = format_mood_for_prompt()
        try:
            prompt = (
                f"Tu n'as pas parle a {user.get('name') or 'ton contact'} "
                f"depuis {silence.days} jours. Envoie-lui un message spontane, "
                "naturel, dans ton style habituel. Pas plus de 2 phrases. "
                "Pas de formule de politesse chiante. Pas de mensonges sur "
                "ce que tu fais."
            )
            response = chat(
                messages=[{"role": "user", "content": prompt}],
                system=SYSTEM_PERSONA.format(
                    context=(
                        f"Tu reprends contact avec {user.get('name') or 'ton contact'} "
                        f"apres {silence.days} jours de silence."
                    ),
                    mood_state=mood_str,
                ),
                max_tokens=150,
            )
        except Exception as e:
            print(f"[task:proactive_ping] LLM failed: {e}")
            continue

        # Envoie
        try:
            send_message(response, phone=user["phone"])
            log_message("whatsapp", "ARIA", "out", response)
            touch_user(user["id"])
            print(f"[task:proactive_ping] Message envoye : {response[:80]!r}")
        except Exception as e:
            print(f"[task:proactive_ping] send failed: {e}")
