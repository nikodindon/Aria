"""
bridge/tts.py — Synthese vocale d'ARIA.

Implementation actuelle : TTS sur le PC Linux (hote), via
speech-dispatcher (spd-say). Permet a ARIA de parler en FR
sans aucune dependance reseau.

Pourquoi pas le TTS Android sur le device ?
  * Pas de Termux sur le Xiaomi dedie
  * Les intents android.speech.tts ne sont pas garantis de
    fonctionner sur toutes les ROMs (MIUI en particulier)
  * Sur le PC on a spd-say (speech-dispatcher + espeak-ng-data)
    qui marche out of the box, offline, en francais

C'est le bon compromis : la "voix" d'ARIA sort des haut-parleurs
du PC, pas du telephone. Si plus tard on veut que ca sorte du
telephone, on remplace speak() par un appel ADB vers un TTS
Android (termux-tts-speak ou app dediee).

Usage :
  from bridge.tts import speak, save_wav, list_voices
  speak("Bonjour Niko")
  save_wav("Bonjour Niko", "/tmp/aria.wav")
"""
import subprocess
import tempfile
from pathlib import Path


DEFAULT_LANG = "fr"
DEFAULT_VOICE = "female1"
SPD_SAY = "spd-say"


def speak(text: str, language: str = DEFAULT_LANG,
          voice: str = DEFAULT_VOICE, rate: int = 0) -> bool:
    """Fait prononcer le texte par speech-dispatcher.

    Retourne True si la commande a reussi (pas de verification
    que le son a effectivement ete joue).

    Parameters :
      text     : le texte a prononcer
      language : code langue ISO ("fr", "en", etc.)
      voice    : type de voix ("female1", "male1", etc.)
      rate     : vitesse de -100 (lent) a +100 (rapide), 0 = normal
    """
    if not text or not text.strip():
        return False
    cmd = [SPD_SAY, "-l", language, "-t", voice, "-r", str(rate), text]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[tts] spd-say failed: {e}")
        return False


def save_wav(text: str, output_path: str,
             language: str = DEFAULT_LANG,
             voice: str = DEFAULT_VOICE,
             rate: int = 0) -> bool:
    """Sauvegarde la synthese en WAV.

    Strategie : utilise ffmpeg pour capturer l'audio de la carte
    son pendant que spd-say parle. C'est pas ideal (on depend
    du hardware audio) mais c'est portable et marche sans
    installer espeak-ng en binaire.

    Alternative si pas d'audio out : passer par spd-say -e (pipe
    mode) + espeak-ng. Mais sans binaire espeak-ng, on fait avec
    ffmpeg.

    Pour une vraie solution offline, installable via apt sans
    sudo, voir : espeak-ng (paquet) + python-espeakng.
    """
    # Si on a espeak-ng en binaire quelque part, on l'utilise direct
    import shutil
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        binary = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
        try:
            subprocess.run(
                [binary, "-v", language, "-w", output_path, text],
                check=True, timeout=30,
            )
            return Path(output_path).exists()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    # Fallback : ffmpeg capture le son de la carte son
    return _record_spk(text, output_path, language, voice, rate)


def _record_spk(text: str, output_path: str,
                language: str, voice: str, rate: int) -> bool:
    """Capture l'audio de la carte son pendant que spd-say parle."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Lance ffmpeg en background, attend un peu, parle, tue ffmpeg
    # Plus simple : on parle d'abord en mesurant, puis on enregistre
    # Approximation : 100ms par caractere pour espeak FR
    duration = max(1.0, len(text) * 0.1)
    try:
        # Lance ffmpeg pour capturer
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-f", "pulse", "-i", "default",
             "-t", str(duration), "-ar", "22050", "-ac", "1",
             "-y", str(output)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # Laisse ffmpeg demarrer
        import time
        time.sleep(0.3)
        # Parle
        speak(text, language=language, voice=voice, rate=rate)
        # Attend la fin de ffmpeg
        ffmpeg.wait(timeout=duration + 2)
        return output.exists() and output.stat().st_size > 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[tts] ffmpeg capture failed: {e}")
        return False


def list_voices() -> list[dict]:
    """Liste les voix disponibles via speech-dispatcher."""
    try:
        result = subprocess.run(
            [SPD_SAY, "-L"], capture_output=True, text=True, timeout=10
        )
        voices = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("NAME") or line.startswith("---"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                voices.append({
                    "name": parts[0],
                    "language": parts[1],
                    "variant": parts[2] if len(parts) > 2 else "",
                })
        return voices
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


if __name__ == "__main__":
    # Test rapide : lister les voix, faire parler ARIA
    print("=== Voix disponibles ===")
    for v in list_voices()[:5]:
        print(f"  {v}")
    print()
    print("=== Test speak ===")
    text = "Bonjour Niko, je suis ARIA. Phase 4 voix operationnelle."
    print(f'Parle: "{text}"')
    speak(text)
    print("OK")
