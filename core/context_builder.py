"""
core/context_builder.py — Assemble le contexte avant chaque appel LLM
"""
from pathlib import Path
from core.memory import get_recent_messages, recall_relevant
from core.personality import format_mood_for_prompt
from plugins import rss_watcher, weather

SYSTEM_PERSONA = Path("prompts/system_persona.txt").read_text()


def build_whatsapp_context(sender: str, message: str) -> tuple[str, list[dict]]:
    """Retourne (system_prompt, messages) prêts pour brain.chat()

    Assemble :
    - system : persona ARIA + mood courant
    - user : prompt de reponse avec l'historique recent (15 derniers
      messages) ET les messages les plus pertinents de l'historique
      long-terme (recherche FTS5 sur le message entrant, top 3)
      ET 5 dernieres news ET la meteo actuelle (si dispo).
    """
    # Memoire court-terme : 15 derniers messages
    recent = get_recent_messages(platform="whatsapp", limit=15)
    history_lines = [
        f"[{'ARIA' if m['direction'] == 'out' else m['sender']}]: {m['content']}"
        for m in recent
    ]
    history_str = "\n".join(history_lines) if history_lines else "(pas d'historique)"

    # Memoire long-terme : top 3 messages les plus pertinents
    # selon FTS5. On prend les mots-cles du message entrant
    # comme requete de recherche. On ne filtre PAS par recent_ids :
    # si un message pertinent est aussi dans l'historique recent,
    # on le montre quand meme (double-emphase, l'important est
    # que le LLM le voit).
    relevant = recall_relevant(message, k=3)
    relevant_lines = [
        f"[{'ARIA' if m['direction'] == 'out' else m['sender']}]: {m['content']}"
        for m in relevant
    ]
    relevant_str = (
        "\n".join(relevant_lines) if relevant_lines
        else "(rien de pertinent dans l'historique long-terme)"
    )

    # Phase 6 : news (5 dernieres stockees en DB)
    news_str = rss_watcher.news_summary_for_prompt(limit=5)

    # Phase 6 : meteo actuelle
    weather_str = weather.weather_for_prompt("Paris")

    mood_str = format_mood_for_prompt()
    system = SYSTEM_PERSONA.format(
        context=f"Tu es en train de répondre à {sender} via WhatsApp.",
        mood_state=mood_str
    )

    reply_prompt = Path("prompts/whatsapp_reply.txt").read_text().format(
        sender=sender,
        message=message,
        history=history_str,
        relevant=relevant_str,
        news=news_str,
        weather=weather_str,
    )

    return system, [{"role": "user", "content": reply_prompt}]
