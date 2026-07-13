"""Tâche : journal du soir + resume envoye par WhatsApp."""
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.brain import chat
from core.context_builder import SYSTEM_PERSONA
from core.memory import (
    get_recent_messages, save_journal, get_current_mood,
    list_users, get_user_by_phone, log_message,
)
from core.personality import format_mood_for_prompt
from bridge.whatsapp import send_message


def run():
    """Tache planifiee (cron) : le soir, ARIA fait son journal et
    envoie un resume a l'user principal via WhatsApp.

    Logique :
    1. Recupere les messages du jour (30 derniers)
    2. Genere une entree de journal via LLM
    3. Sauvegarde en DB
    4. Envoie un resume court au user le plus recent
    """
    print("[task:evening_digest] Demarrage...")
    today = date.today().isoformat()
    msgs = get_recent_messages(limit=30)
    if not msgs:
        print("[task:evening_digest] Pas de messages, skip.")
        return

    # Genere le journal
    conversations_summary = "\n".join(
        f"[{'ARIA' if m['direction'] == 'out' else m['sender']}] {m['content'][:80]}"
        for m in msgs
    ) or "(aucune conversation)"
    mood = get_current_mood()
    mood_str = format_mood_for_prompt()

    prompt_tpl_path = Path("prompts/journal_entry.txt")
    if prompt_tpl_path.exists():
        prompt_tpl = prompt_tpl_path.read_text()
        prompt = prompt_tpl.format(
            date=today,
            events_summary="(events à implémenter)",
            conversations_summary=conversations_summary,
            mood_timeline=mood_str,
        )
    else:
        prompt = (
            f"Tu es ARIA. Redige ton journal intime du {today}.\n\n"
            f"Conversations de la journee :\n{conversations_summary}\n\n"
            f"State d'esprit actuel : {mood_str}\n\n"
            "Ecris une entree de journal courte (5-10 lignes), en francais, "
            "a la premiere personne, avec ta personnalite. Pas de liste a "
            "puces, du texte fluide."
        )

    try:
        entry = chat(
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PERSONA.format(
                context=f"Tu ecris ton journal intime du soir ({today}).",
                mood_state=mood_str,
            ),
            max_tokens=400,
        )
    except Exception as e:
        print(f"[task:evening_digest] LLM failed: {e}")
        return

    save_journal(today, entry, mood.get("mood", "neutre"))
    log_message("whatsapp", "ARIA", "out_internal", f"[journal] {entry[:200]}")
    print(f"[task:evening_digest] Journal sauvegarde pour {today} ({len(entry)} chars)")

    # Envoie un resume court au user le plus recent
    users = list_users()
    if not users:
        print("[task:evening_digest] Aucun user appaire, pas d'envoi.")
        return
    target = users[0]  # le plus recent (ORDER BY last_seen DESC)
    name = target.get("name") or target["phone"]
    summary = f"Bonsoir {name}, voici mon resume du jour :\n\n{entry[:500]}"
    try:
        send_message(summary, phone=target["phone"])
        log_message("whatsapp", "ARIA", "out", summary)
        print(f"[task:evening_digest] Resume envoye a {name}")
    except Exception as e:
        print(f"[task:evening_digest] send failed: {e}")
