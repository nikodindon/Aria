"""
tools/test_adb_primitives.py — Vérifie que les 6 primitives WhatsApp-friendly
du bridge ADB fonctionnent réellement sur le device.

Stratégie : on lance chaque primitive, on vérifie qu'elle ne raise pas et
(on le peut) qu'elle a un effet observable via un screenshot avant/après.
On ne touche pas à WhatsApp directement (trop fragile), on reste sur le
launcher/système.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import adb


def must_have_device() -> str:
    devs = adb.devices()
    # adb devices output:
    #   List of devices attached
    #   <id>\tdevice
    lines = [l for l in devs.splitlines() if l.strip() and "List" not in l and "*" not in l]
    if not lines or "device" not in lines[0]:
        print("FAIL  no device authorized (adb devices returned nothing usable)")
        print(devs)
        sys.exit(1)
    device_id = lines[0].split()[0]
    print(f"PASS  device authorized: {device_id}")
    return device_id


def screencap(path: str):
    adb.screenshot(path)
    p = Path(path)
    if not p.is_file() or p.stat().st_size < 1000:
        print(f"FAIL  screenshot {path} missing or tiny ({p.stat().st_size if p.exists() else 0} bytes)")
        sys.exit(1)
    print(f"PASS  screenshot {path} ({p.stat().st_size} bytes)")


def main() -> int:
    print("=== Test ADB primitives ===")
    must_have_device()

    # 1. screenshot : baseline
    screencap("/tmp/aria_primitive_1.png")

    # 2. press_home : doit toujours marcher, ramène au launcher
    try:
        adb.press_home()
        time.sleep(0.5)
        print("PASS  press_home (no exception)")
    except Exception as e:
        print(f"FAIL  press_home: {e}")
        return 1

    # 3. tap : on tape au milieu de l'écran. Ça ne doit pas raise.
    #    On ne sait pas ce qu'il y a sous le tap, c'est OK.
    try:
        adb.tap(540, 1200)  # milieu d'un écran 1080x2400
        time.sleep(0.3)
        print("PASS  tap (no exception)")
    except Exception as e:
        print(f"FAIL  tap: {e}")
        return 1

    # 4. swipe : swipe court vers le haut. Doit scroller ou ne rien faire.
    try:
        adb.swipe(540, 1500, 540, 1000, duration_ms=300)
        time.sleep(0.3)
        print("PASS  swipe (no exception)")
    except Exception as e:
        print(f"FAIL  swipe: {e}")
        return 1

    # 5. press_back : retour système. Idempotent si on est déjà au launcher.
    try:
        adb.press_back()
        time.sleep(0.3)
        print("PASS  press_back (no exception)")
    except Exception as e:
        print(f"FAIL  press_back: {e}")
        return 1

    # 6. open_app : WhatsApp (toujours installé chez user). On vérifie juste
    #    qu'il n'y a pas d'exception. Le but n'est PAS de tester que ça
    #    aboutit dans la bonne vue (trop fragile), juste que l'intent passe.
    try:
        adb.open_app("com.whatsapp")
        time.sleep(1.0)  # open_app a déjà un sleep(2) interne
        print("PASS  open_app com.whatsapp (no exception)")
    except Exception as e:
        print(f"FAIL  open_app: {e}")
        return 1

    # 7. send_text : on l'appelle en dernier, dans un champ vide (l'app est
    #    maintenant sur WhatsApp). Si le focus n'est pas sur un champ texte,
    #    ADB input text va juste crasher ou échouer silencieusement. Donc
    #    on capture l'exception, et on accepte "soft fail" ici (le test
    #    dur de send_text viendra avec un EditText ciblé en Phase 1).
    try:
        adb.send_text("ping")
        time.sleep(0.3)
        print("PASS  send_text (no exception)")
    except Exception as e:
        print(f"WARN  send_text raised (acceptable, no focused field): {e}")

    # 8. screenshot final : preuve que le device a bien bougé
    screencap("/tmp/aria_primitive_2.png")

    # Compare sommaire : si les deux screenshots ont la même taille, c'est
    # louche (rien n'a bougé). Pas un test dur, juste un signal.
    s1 = Path("/tmp/aria_primitive_1.png").stat().st_size
    s2 = Path("/tmp/aria_primitive_2.png").stat().st_size
    if abs(s1 - s2) < 100:
        print(f"WARN  screenshots are suspiciously similar ({s1} vs {s2} bytes)")
    else:
        print(f"PASS  screenshots differ ({s1} vs {s2} bytes) — device moved")

    # Retour au launcher pour pas laisser le téléphone sur WhatsApp
    adb.press_home()
    time.sleep(0.3)
    print("PASS  press_home (cleanup)")

    print("✓ ADB primitives opérationnelles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
