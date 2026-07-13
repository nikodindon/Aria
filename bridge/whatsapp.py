"""
bridge/whatsapp.py — Interaction WhatsApp via ADB + OCR.

API publique :
  * list_conversations(screenshot_path=None) -> list[dict]
        Snapshot de la vue Discussions. Chaque entrée :
          {name, timestamp, preview, badge, y_center, x_center}
        y_center / x_center sont les coords de tap (relatives au
        screenshot, directement utilisables par adb.tap()).

  * open_conversation(name: str) -> bool
        Ouvre la conversation dont le nom matche. Tap sur le
        y_center de la ligne. Retourne True si tap exécuté.

  * current_view() -> str
        Heuristique grossière de la vue courante. Utile pour
        décider quoi faire ensuite (Phase 1.4 : envoyer un
        message requiert d'être dans une conversation ouverte).

Approche : on évite de reconstruire l'état interne (cache). Chaque
appel prend un screenshot frais et lit la vue. C'est plus lent
mais beaucoup plus simple à raisonner — et l'UI WhatsApp change
suffisamment souvent (badges qui apparaissent/disparaissent) qu'un
cache serait une source de bugs.
"""
import re
import time
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image

from bridge import adb

WA_PACKAGE = "com.whatsapp"

# Resolution cible (1080x2400 = Xiaomi/Acer recentes). Sur d'autres
# resolutions, les coordonnees de crop doivent etre recalculees.
DEFAULT_W, DEFAULT_H = 1080, 2400
LIST_TOP = 290
LIST_BOTTOM = 2200

# Regex pour distinguer une vraie conversation d'un element d'UI fixe.
# Une conversation a : un nom (mot capitalise) + un timestamp au format
# HH:MM (aujourd'hui) ou DD/MM/YYYY (plus ancien).
TS_RE = re.compile(r"\b(\d{1,2}:\d{2}|\d{2}/\d{2}/\d{4})\b")


def _screenshot(path: str = "/tmp/aria_wa_list.png") -> Path:
    adb.screenshot(path)
    p = Path(path)
    if not p.is_file() or p.stat().st_size < 1000:
        raise RuntimeError(f"adb screenshot a échoué : {path}")
    return p


def _crop_list(img: Image.Image) -> Image.Image:
    w, h = img.size
    if (w, h) != (DEFAULT_W, DEFAULT_H):
        # On redimensionne pour que le reste du code marche avec des
        # coords absolues 1080x2400. Phase 1.2+ : passer en coords
        # relatives pour ne plus avoir ce couplage à la résolution.
        img = img.resize((DEFAULT_W, DEFAULT_H))
    return img.crop((0, LIST_TOP, DEFAULT_W, LIST_BOTTOM))


def _ocr_rows(crop: Image.Image) -> list[dict]:
    """OCR + groupement en lignes par proximité verticale.

    Retourne une liste de {"top", "text", "y_center"} triée par top.
    y_center est la coordonnée dans le screenshot ORIGINAL (1080x2400),
    pas dans le crop.
    """
    data = pytesseract.image_to_data(
        crop, lang="fra", output_type=pytesseract.Output.DICT
    )
    n = len(data["text"])
    words = []
    for i in range(n):
        txt = data["text"][i].strip()
        try:
            conf = float(data["conf"][i])
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
    words.sort(key=lambda w: (w["top"], w["left"]))

    lines: list[list[dict]] = []
    for w in words:
        placed = False
        for line in lines:
            ref = line[0]
            if abs(w["top"] - ref["top"]) <= max(ref["height"], w["height"]) // 2:
                line.append(w)
                placed = True
                break
        if not placed:
            lines.append([w])

    rows = []
    for line in lines:
        line.sort(key=lambda w: w["left"])
        text = " ".join(w["text"] for w in line)
        # Conversion top dans crop -> y_center dans screenshot original
        top_in_screenshot = line[0]["top"] + LIST_TOP
        rows.append({
            "top": top_in_screenshot,
            "text": text,
            "y_center": top_in_screenshot + line[0]["height"] // 2,
        })
    rows.sort(key=lambda r: r["top"])
    return rows


# --- read_conversation -----------------------------------------------------

# Regex conservative pour redacter les codes/credentials typiques
# (codes de verif, OTP, PINs). On remplace un run de 4-8 chiffres
# isoles par [REDACTED]. Les numeros plus courts ou plus longs passent.
_CREDENTIAL_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")


def redact_credentials(text: str) -> str:
    """Masque les credentials typiques dans un texte.

    Politique conservative : on remplace un run de 4-8 chiffres (pas
    dans un nombre plus long, ex. pas dans 12345678901) par
    [REDACTED]. Si on a redacted quelque chose, on ajoute un marqueur
    "[REDACTED]" en fin pour que le caller sache que la valeur est
    masquee et qu'il ne doit pas la prendre pour la valeur reelle.
    """
    redacted = _CREDENTIAL_RE.sub("[REDACTED]", text)
    if redacted != text:
        return redacted + " [REDACTED]"
    return redacted


def read_conversation(screenshot_path: Optional[str] = None) -> list[dict]:
    """
    Lit les messages visibles dans une conversation WhatsApp ouverte.

    Heuristique Phase 1.3 :
      - Crop la zone messages (y=[280, 2150] sur 1080x2400).
      - OCR mot par mot avec image_to_data.
      - Groupement en messages : un nouveau message demarre quand
        le gap vertical entre deux mots consecutifs depasse 1.5x la
        hauteur moyenne d'un mot.
      - Direction : position du bord gauche. < 270 =recu (gauche),
        > 810 =envoye (droite), sinon unknown.
      - Timestamp : dernier mot du message, si format HH:MM.
      - Credentials redactes via redact_credentials().

    Note : suppose qu'on est DANS une conversation ouverte. Si on
    est sur la vue Discussions, l'OCR produit du garbage. Le caller
    doit verifier current_view() == "conversation" en amont.
    """
    png = Path(screenshot_path) if screenshot_path else _screenshot()
    img = Image.open(png)
    w, h = img.size
    if (w, h) != (DEFAULT_W, DEFAULT_H):
        img = img.resize((DEFAULT_W, DEFAULT_H))

    MSG_TOP = 280
    MSG_BOTTOM = 2150
    crop = img.crop((0, MSG_TOP, DEFAULT_W, MSG_BOTTOM))

    data = pytesseract.image_to_data(
        crop, lang="fra", output_type=pytesseract.Output.DICT
    )
    n = len(data["text"])
    words = []
    for i in range(n):
        txt = data["text"][i].strip()
        try:
            conf = float(data["conf"][i])
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
    if not words:
        return []

    avg_h = sum(w["height"] for w in words) / len(words)
    gap_threshold = int(avg_h * 1.5)
    words.sort(key=lambda w: (w["top"], w["left"]))

    # Groupement en messages : on coupe quand le gap vertical entre
    # le mot precedent et le mot courant depasse le seuil.
    messages: list[list[dict]] = []
    current: list[dict] = [words[0]]
    for w in words[1:]:
        prev = current[-1]
        vertical_gap = w["top"] - (prev["top"] + prev["height"])
        if vertical_gap > gap_threshold:
            messages.append(current)
            current = [w]
        else:
            current.append(w)
    messages.append(current)

    result = []
    for msg_words in messages:
        msg_words_sorted = sorted(msg_words, key=lambda w: (w["top"], w["left"]))
        text = " ".join(w["text"] for w in msg_words_sorted)

        min_left = min(w["left"] for w in msg_words_sorted)
        if min_left < 270:
            direction = "in"
        elif min_left > 810:
            direction = "out"
        else:
            direction = "unknown"

        time_str = ""
        if msg_words_sorted:
            last = msg_words_sorted[-1]["text"]
            if re.match(r"^\d{1,2}:\d{2}$", last):
                time_str = last

        y_center = msg_words_sorted[0]["top"] + msg_words_sorted[0]["height"] // 2 + MSG_TOP

        if time_str:
            text = text[: -len(time_str)].strip()

        result.append({
            "direction": direction,
            "text": redact_credentials(text),
            "time": time_str,
            "y_center": y_center,
        })

    return result


def list_conversations(screenshot_path: Optional[str] = None) -> list[dict]:
    """
    Lit la vue Discussions de WhatsApp et retourne la liste des conversations.

    Une conversation est identifiée par la présence d'un timestamp au
    format HH:MM ou DD/MM/YYYY dans la ligne. La ligne SUIVANTE (si
    elle existe et n'est pas elle-même un timestamp) est considérée
    comme l'aperçu du dernier message.

    Heuristique volontairement simple : Phase 1.1. Une conversation =
    1 à 2 lignes OCR. Si l'aperçu contient [N], on le retire du
    texte et on l'expose comme badge.

    Retourne une liste vide si la vue ne ressemble pas à Discussions.
    """
    png = Path(screenshot_path) if screenshot_path else _screenshot()
    img = Image.open(png)
    crop = _crop_list(img)
    rows = _ocr_rows(crop)

    # Filtrer pour ne garder que les lignes qui sont des conversations
    # (= qui contiennent un timestamp).
    ts_rows = [r for r in rows if TS_RE.search(r["text"])]
    if not ts_rows:
        return []

    # Pour chaque ligne "timestamp", regarder si la suivante (dans rows)
    # peut être un aperçu. On travaille sur l'index dans rows.
    conversations = []
    for r in ts_rows:
        # Nom = tout sauf le timestamp
        name = TS_RE.sub("", r["text"]).strip()
        # Nettoie le nom des artefacts OCR typiques (lettre d'avatar
        # collée, ponctuation isolée)
        name = re.sub(r"^[A-Z]\s+", "", name).strip()
        if not name:
            continue

        # Aperçu = ligne suivante si elle existe, n'est pas elle-même
        # une ligne-timestamp, et n'est pas un texte d'UI fixe
        # (heuristique : si elle contient un timestamp, c'est pas un
        # aperçu, c'est une autre conversation).
        preview = ""
        badge = 0
        # On cherche dans rows (la liste complète) la ligne qui suit r
        try:
            idx_in_rows = rows.index(r)
            if idx_in_rows + 1 < len(rows):
                nxt = rows[idx_in_rows + 1]
                if not TS_RE.search(nxt["text"]):
                    preview_text = nxt["text"]
                    # Badge [N]
                    m = re.search(r"\[(\d+)\]", preview_text)
                    if m:
                        badge = int(m.group(1))
                        preview_text = re.sub(r"\[\d+\]", "", preview_text).strip()
                    preview = preview_text
        except ValueError:
            pass

        # mypy/pyright : le re.search retourne match | None, on .group
        # seulement si on a matché. Le TS_RE.search filtré en amont
        # garantit qu'on est ici dans la branche match.
        ts_match = TS_RE.search(r["text"])
        ts_value = ts_match.group(1) if ts_match else ""

        conversations.append({
            "name": name,
            "timestamp": ts_value,
            "preview": preview,
            "badge": badge,
            "y_center": r["y_center"],
            "x_center": DEFAULT_W // 2,
        })

    return conversations


def open_conversation(name: str, screenshot_path: Optional[str] = None) -> bool:
    """
    Ouvre la conversation dont le nom matche (case-insensitive substring).
    Retourne True si un tap a été effectué.
    """
    convs = list_conversations(screenshot_path)
    needle = name.lower()
    for c in convs:
        if needle in c["name"].lower():
            adb.tap(c["x_center"], c["y_center"])
            time.sleep(0.5)
            return True
    return False


def current_view() -> str:
    """
    Heuristique très grossière basée sur le contenu OCR de l'écran
    courant. Utile pour sanity-check avant une action (Phase 1.4).

    Retourne : "discussions" | "conversation" | "other"

    Heuristique :
      - "discussions" : on voit la barre de recherche Meta AI
        ("demander à meta") ET la tab bar (actus/appels/communautes).
      - "conversation" : on voit le placeholder du champ de saisie
        ("message" seul, ou "saisir un message"). C'est volontairement
        large : on accepte plusieurs variantes du placeholder selon
        les versions de WA.
    """
    png = _screenshot()
    img = Image.open(png)
    # OCR rapide sur tout l'écran (full, pas crop) — cher mais fiable
    text = pytesseract.image_to_string(img, lang="fra").lower()
    if "demander à meta" in text or ("discussions" in text and "actus" in text):
        return "discussions"
    # Placeholder champ de saisie. Variantes : "message", "saisir un message",
    # "taper un message". On cherche le SINGULIER "message" en mot isole
    # (suivi d'espace ou en fin de ligne) pour eviter les faux positifs
    # ("messages personnels sont chiffres" et "gerer les messages" du
    # card de bienvenue business).
    if re.search(r"\bmessage\b", text) and "personnels" not in text and "gérer" not in text:
        return "conversation"
    # Fallback : indices d'une conversation ouverte. La card de bienvenue
    # business contient "compte professionnel" + "membre depuis", et
    # les messages bulles contiennent "code de vérification" (typique
    # des messages de service). On accepte l'un OU l'autre comme preuve.
    if "compte professionnel" in text or "code de vérification" in text:
        return "conversation"
    return "other"
