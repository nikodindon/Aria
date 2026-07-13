"""Tâche : ARIA prend l'initiative de t'écrire si trop de silence."""
import os
from datetime import datetime, timedelta
from core.memory import get_recent_messages
from core.brain import complete
from dotenv import load_dotenv

load_dotenv()

SILENCE_HOURS = int(os.getenv("PROACTIVE_SILENCE_HOURS", 48))
YOUR_PHONE = os.getenv("YOUR_PHONE_NUMBER", "")


def run():
    msgs = get_recent_messages(platform="whatsapp", limit=5)
    if not msgs:
        return

    last_ts = datetime.fromisoformat(msgs[-1]["ts"])
    silence = datetime.now() - last_ts

    if silence > timedelta(hours=SILENCE_HOURS):
        print(f"[task:proactive_ping] {silence.days}j de silence — ARIA prend l'initiative.")
        prompt = f"Tu n'as pas parlé à ton interlocuteur depuis {silence.days} jours. Envoie-lui un message spontané, naturel, dans ton style habituel. Pas plus de 2 phrases."
        msg = complete(prompt, max_tokens=100)
        print(f"[task:proactive_ping] Message : {msg}")
        # bridge.whatsapp.send_via_deeplink(YOUR_PHONE, msg)
