"""
core/personality.py — Gestion de la personnalité et de l'état émotionnel d'ARIA
"""
import json
from pathlib import Path
from core.brain import complete
from core.memory import get_current_mood, save_mood, get_recent_messages

MOOD_PROMPT = Path("prompts/mood_update.txt").read_text()


def get_mood_state() -> dict:
    return get_current_mood()


def update_mood(weather: str = "inconnue", time_of_day: str = "journée"):
    recent = get_recent_messages(limit=10)
    events = "\n".join([f"[{m['direction']}] {m['sender']}: {m['content'][:100]}" for m in recent])

    prompt = MOOD_PROMPT.format(
        recent_events=events or "Rien de notable.",
        weather=weather,
        time_of_day=time_of_day
    )
    try:
        raw = complete(prompt, max_tokens=150)
        data = json.loads(raw)
        save_mood(data["mood"], data["energy"], data["curiosity"], data.get("reason", ""))
        return data
    except Exception as e:
        print(f"[personality] Erreur mise à jour humeur : {e}")
        return get_current_mood()


def format_mood_for_prompt() -> str:
    m = get_current_mood()
    return f"Humeur : {m.get('mood','?')} | Énergie : {m.get('energy','?')} | Curiosité : {m.get('curiosity','?')}"
