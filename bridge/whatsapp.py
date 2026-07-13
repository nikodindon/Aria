"""
bridge/whatsapp.py — Interaction WhatsApp via ADB + OCR
TODO: implémenter la lecture OCR des messages entrants
"""
import time
from bridge.adb import open_app, screenshot, tap, send_text, wake_screen
from core.memory import log_message

WA_PACKAGE = "com.whatsapp"


def open_whatsapp():
    wake_screen()
    open_app(WA_PACKAGE)
    time.sleep(2)


def send_message(contact_name: str, message: str):
    """
    Envoie un message à un contact WhatsApp.
    Nécessite d'être déjà sur l'écran principal de WA.
    """
    # TODO: implémenter la navigation vers le contact
    # Option 1 : deep link WhatsApp (recommandé)
    # Option 2 : OCR + tap sur le contact
    raise NotImplementedError("À implémenter — voir bridge/whatsapp.py")


def send_via_deeplink(phone_number: str, message: str):
    """Envoie via deep link WhatsApp (plus fiable que l'UI)."""
    from bridge.adb import _adb
    import urllib.parse
    encoded = urllib.parse.quote(message)
    url = f"https://api.whatsapp.com/send?phone={phone_number}&text={encoded}"
    _adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url)
    time.sleep(3)
    # Taper sur le bouton Envoyer (coordonnées à calibrer selon la résolution)
    tap(1000, 2100)  # adapter à la résolution de ton écran
    log_message("whatsapp", "ARIA", "out", message)


def read_messages_ocr() -> list[dict]:
    """
    Lit les messages visibles à l'écran via OCR.
    Retourne une liste de {"sender": str, "content": str}
    TODO: implémenter
    """
    raise NotImplementedError("OCR WhatsApp à implémenter")
