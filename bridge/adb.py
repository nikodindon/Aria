"""
bridge/adb.py — Primitives ADB pour piloter le téléphone
"""
import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DEVICE = os.getenv("ADB_DEVICE_ID", "")
ADB = os.getenv("ADB_PATH", "adb")


def _adb(*args, check: bool = False) -> str:
    """Run an adb command and return stdout.

    By default, stderr is captured and discarded silently (legacy).
    Pass check=True to raise CalledProcessError on non-zero exit AND
    to include stderr in the exception message. Use check=True for
    any command whose success matters (e.g. `input tap`).
    """
    cmd = [ADB]
    if DEVICE:
        cmd += ["-s", DEVICE]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    return result.stdout.strip()


def devices() -> str:
    return subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout


def screenshot(path: str = "/tmp/aria_screen.png") -> str:
    """Capture l'écran et le récupère en local."""
    _adb("shell", "screencap", "-p", "/sdcard/aria_tmp.png")
    _adb("pull", "/sdcard/aria_tmp.png", path)
    return path


def tap(x: int, y: int):
    _adb("shell", "input", "tap", str(x), str(y), check=True)
    time.sleep(0.3)


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    _adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms), check=True)


def send_text(text: str):
    """Envoie du texte dans le champ actif (échappe les caractères spéciaux)."""
    escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
    _adb("shell", "input", "text", escaped, check=True)


def press_back():
    _adb("shell", "input", "keyevent", "4", check=True)


def press_home():
    _adb("shell", "input", "keyevent", "3", check=True)


def open_app(package: str):
    _adb("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(2)


def wake_screen():
    _adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    time.sleep(0.5)
    # Swipe pour déverrouiller (adapter selon le téléphone)
    swipe(540, 1800, 540, 900, 400)
    time.sleep(0.5)
