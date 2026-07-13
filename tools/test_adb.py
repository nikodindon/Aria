"""Vérifie que ADB fonctionne et que le téléphone est détecté."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge.adb import devices, screenshot

print("=== Test ADB ===")
print(devices())
print("\nCapture d'écran test...")
path = screenshot("/tmp/aria_test.png")
print(f"Screenshot sauvegardé : {path}")
print("✓ ADB opérationnel")
