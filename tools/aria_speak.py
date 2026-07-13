"""
tools/aria_speak.py — CLI pour faire parler ARIA.

Usage :
  python tools/aria_speak.py "Bonjour Niko"
  python tools/aria_speak.py "Salut" --voice male1 --rate -10
  python tools/aria_speak.py "Hello" --language en
  python tools/aria_speak.py "Test" --save /tmp/aria.wav
  python tools/aria_speak.py --list-voices

Fait prononcer du texte par ARIA via speech-dispatcher.
Optionnellement sauvegarde en WAV.
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge.tts import speak, save_wav, list_voices


def main() -> int:
    parser = argparse.ArgumentParser(description="ARIA speak (TTS)")
    parser.add_argument("text", nargs="?", help="Texte a prononcer")
    parser.add_argument("--language", default="fr",
                        help="Code langue (defaut: fr)")
    parser.add_argument("--voice", default="female1",
                        help="Type de voix (female1, male1, ...)")
    parser.add_argument("--rate", type=int, default=0,
                        help="Vitesse -100 a +100 (defaut: 0)")
    parser.add_argument("--save", metavar="PATH",
                        help="Sauvegarder en WAV au lieu de jouer")
    parser.add_argument("--list-voices", action="store_true",
                        help="Lister les voix disponibles")
    args = parser.parse_args()

    if args.list_voices:
        voices = list_voices()
        if not voices:
            print("Aucune voix trouvee (spd-say disponible ?)")
            return 1
        for v in voices:
            print(f"  {v['name']:30s} {v['language']:5s} {v['variant']}")
        return 0

    if not args.text:
        parser.print_help()
        return 1

    print(f'"{args.text}"')
    print(f"  lang={args.language} voice={args.voice} rate={args.rate}")
    if args.save:
        ok = save_wav(args.text, args.save,
                      language=args.language,
                      voice=args.voice, rate=args.rate)
        print(f"  save: {'OK' if ok else 'FAIL'} -> {args.save}")
        return 0 if ok else 1
    else:
        ok = speak(args.text,
                   language=args.language,
                   voice=args.voice, rate=args.rate)
        print(f"  speak: {'OK' if ok else 'FAIL'}")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
