"""Tâche : journal du soir + résumé envoyé par WhatsApp."""
from datetime import date
from pathlib import Path
from core.brain import complete
from core.memory import get_recent_messages, save_journal, get_current_mood


def run():
    print("[task:evening_digest] Rédaction du journal du soir...")
    today = date.today().isoformat()
    msgs = get_recent_messages(limit=30)
    summary = "\n".join([f"[{m['direction']}] {m['content'][:80]}" for m in msgs])
    mood = get_current_mood()

    prompt_tpl = Path("prompts/journal_entry.txt").read_text()
    prompt = prompt_tpl.format(
        date=today,
        events_summary="(events à implémenter)",
        conversations_summary=summary or "(aucune conversation)",
        mood_timeline=mood.get("mood", "neutre")
    )
    entry = complete(prompt, max_tokens=300)
    save_journal(today, entry, mood.get("mood", "neutre"))
    print(f"[task:evening_digest] Journal sauvegardé pour {today}.")
