"""
core/context_builder.py — Assemble le contexte avant chaque appel LLM
"""
from pathlib import Path
from core.memory import get_recent_messages
from core.personality import format_mood_for_prompt

SYSTEM_PERSONA = Path("prompts/system_persona.txt").read_text()


def build_whatsapp_context(sender: str, message: str) -> tuple[str, list[dict]]:
    """Retourne (system_prompt, messages) prêts pour brain.chat()"""
    recent = get_recent_messages(platform="whatsapp", limit=15)
    history_lines = [
        f"[{'ARIA' if m['direction'] == 'out' else m['sender']}]: {m['content']}"
        for m in recent
    ]
    history_str = "\n".join(history_lines) if history_lines else "(pas d'historique)"
    mood_str = format_mood_for_prompt()

    system = SYSTEM_PERSONA.format(
        context=f"Tu es en train de répondre à {sender} via WhatsApp.",
        mood_state=mood_str
    )

    reply_prompt = Path("prompts/whatsapp_reply.txt").read_text().format(
        sender=sender,
        message=message,
        history=history_str
    )

    return system, [{"role": "user", "content": reply_prompt}]
