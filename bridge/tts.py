"""
bridge/tts.py — Synthèse vocale sur le device Android
"""
from bridge.adb import _adb


def speak(text: str, language: str = "fr-FR"):
    """
    Utilise le TTS Android natif pour faire parler le téléphone.
    """
    escaped = text.replace("'", "\\'")
    _adb(
        "shell",
        "am", "start",
        "-a", "android.intent.action.SEND",
        "--es", "android.intent.extra.TEXT", escaped,
    )
    # Alternative plus simple : app TTS via intent
    _adb(
        "shell",
        "am", "broadcast",
        "-a", "android.speech.tts.SPEAK",
        "--es", "text", escaped,
        "--es", "lang", language,
    )


def speak_via_termux(text: str):
    """
    Si Termux est installé sur le device, utilise termux-tts-speak.
    Plus propre et configurable.
    """
    escaped = text.replace('"', '\\"')
    _adb("shell", f'am broadcast --user 0 -a com.termux.tts --es text "{escaped}"')
