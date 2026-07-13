"""Tâche : vérifier les messages WhatsApp entrants et y répondre."""
from core.brain import chat
from core.context_builder import build_whatsapp_context
from core.memory import log_message


def run():
    print("[task:check_messages] Vérification des messages...")
    # TODO: implémenter la lecture OCR des messages entrants
    # Exemple de flow attendu :
    # messages = bridge.whatsapp.read_messages_ocr()
    # for msg in messages:
    #     system, msgs = build_whatsapp_context(msg["sender"], msg["content"])
    #     reply = chat(msgs, system=system)
    #     log_message("whatsapp", msg["sender"], "in", msg["content"])
    #     bridge.whatsapp.send_message(msg["sender"], reply)
    #     log_message("whatsapp", "ARIA", "out", reply)
    pass
