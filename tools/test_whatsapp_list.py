"""
tools/test_whatsapp_list.py — Lit la liste des conversations WhatsApp.

Stratégie Phase 1.1 :
  1. Screenshot de l'écran actuel (on suppose qu'on est sur Discussions).
  2. Crop de la zone de la liste (entre la barre de recherche et la tab bar).
  3. OCR via pytesseract.image_to_data() pour récupérer texte + coordonnées.
  4. Reconstruction des lignes (groupement par position verticale).
  5. Pour chaque ligne, on tente d'extraire : nom, badge non-lus, dernier message.

Ce script est un premier jet : il affiche ce qu'il a trouvé, ne prétend pas
être parfait. Il sert à valider que la stratégie OCR est viable avant
de promouvoir le code dans bridge/whatsapp.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import adb
from PIL import Image
import pytesseract

# Résolution cible (récupérée via `adb shell wm size` : 1080x2400)
# Sur d'autres résolutions, il faudra adapter ces zones. Phase 1.1 = codé
# en dur, Phase 1.2 = détection dynamique.
W, H = 1080, 2400
# Zone "liste des discussions" : entre la search bar (y≈270) et la tab
# bar (y≈2230). Marge de sécurité de chaque côté.
LIST_TOP = 290
LIST_BOTTOM = 2200


def screenshot_wa_discussions(path: str = "/tmp/aria_wa_list.png") -> Path:
    """Ouvre WhatsApp (si pas déjà fait) et screenshot la vue Discussions."""
    p = Path(path)
    # On ne lance pas open_app si WhatsApp est déjà au premier plan :
    # un monkey call relance l'app, ce qui reset la vue. On s'appuie
    # donc sur le fait que l'utilisateur a lancé WhatsApp avant.
    # (Le test persona + le test ADB primitives ont déjà ouvert WA, donc
    #  l'app est normalement au premier plan.)
    adb.screenshot(path)
    if not p.is_file() or p.stat().st_size < 1000:
        raise RuntimeError(f"screenshot failed: {path}")
    return p


def crop_list(png: Path) -> Image.Image:
    """Crop la zone liste de conversations."""
    img = Image.open(png)
    if img.size != (W, H):
        print(f"WARN  screenshot is {img.size}, attendu (1080, 2400). "
              f"Le crop sera approximatif.")
        # On scale à 1080x2400 si la résolution diffère
        img = img.resize((W, H))
    return img.crop((0, LIST_TOP, W, LIST_BOTTOM))


def extract_rows(crop: Image.Image) -> list[dict]:
    """
    OCR par mot, groupement en lignes par proximité verticale.
    Retourne une liste de {"text": "..."} par ligne, en ordre de lecture.
    """
    data = pytesseract.image_to_data(
        crop, lang="fra", output_type=pytesseract.Output.DICT
    )
    n = len(data["text"])
    # Filtre : on garde les mots avec confiance raisonnable et non vides
    words = []
    for i in range(n):
        txt = data["text"][i].strip()
        conf_str = data["conf"][i]
        try:
            conf = float(conf_str)
        except (ValueError, TypeError):
            conf = -1
        if not txt or conf < 30:
            continue
        words.append({
            "text": txt,
            "top": data["top"][i],
            "left": data["left"][i],
            "height": data["height"][i],
        })

    # Groupement en lignes : mots avec top qui se chevauchent (overlap vertical)
    # sont sur la même ligne.
    words.sort(key=lambda w: (w["top"], w["left"]))
    lines: list[list[dict]] = []
    for w in words:
        placed = False
        for line in lines:
            ref = line[0]
            # Tolérance : demi-hauteur d'un mot
            if abs(w["top"] - ref["top"]) <= max(ref["height"], w["height"]) // 2:
                line.append(w)
                placed = True
                break
        if not placed:
            lines.append([w])

    # Tri par top puis left, et reconstruction du texte
    rows = []
    for line in lines:
        line.sort(key=lambda w: w["left"])
        rows.append({
            "top": line[0]["top"],
            "text": " ".join(w["text"] for w in line),
        })
    rows.sort(key=lambda r: r["top"])
    return rows


def main() -> int:
    print("=== Test WhatsApp list (Phase 1.1) ===")
    print(f"Résolution cible : {W}x{H}")
    print(f"Zone liste : y=[{LIST_TOP}, {LIST_BOTTOM}]")

    # 1. Screenshot
    try:
        png = screenshot_wa_discussions()
        print(f"PASS  screenshot : {png} ({png.stat().st_size} bytes)")
    except Exception as e:
        print(f"FAIL  screenshot : {e}")
        return 1

    # 2. Crop
    crop = crop_list(png)
    crop_path = Path("/tmp/aria_wa_list_crop.png")
    crop.save(crop_path)
    print(f"PASS  crop sauvegardé : {crop_path} ({crop.size})")

    # 3. OCR + groupement en lignes
    rows = extract_rows(crop)
    print(f"PASS  {len(rows)} lignes détectées")
    for i, r in enumerate(rows):
        print(f"  [{i:2d}] y={r['top']:4d}  {r['text']!r}")

    # 4. Sanity check : on doit voir au moins 1 conversation (les 2 attendues :
    # "WhatsApp" et "PayPal"). Si on en a 0, c'est que le crop ou l'OCR a raté.
    has_wa = any("WhatsApp" in r["text"] for r in rows)
    has_paypal = any("PayPal" in r["text"] for r in rows)
    if not has_wa and not has_paypal:
        print("FAIL  aucune conversation détectée (ni WhatsApp ni PayPal).")
        print("      Le crop ou l'OCR a un problème — vérifier le screenshot.")
        return 1

    found = []
    if has_wa:
        found.append("WhatsApp")
    if has_paypal:
        found.append("PayPal")
    print(f"✓ Conversations détectées : {', '.join(found)}")
    print("✓ Phase 1.1 stratégie viable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
