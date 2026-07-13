#!/usr/bin/env bash
# ============================================================
#  ARIA — init_project.sh
#  Initialise l'arborescence complète du projet
# ============================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   ARIA — Autonomous Roaming Agent     ║"
echo "  ║         Project Initializer           ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ── Dossiers ──────────────────────────────────────────────
echo -e "${YELLOW}▸ Création de l'arborescence...${NC}"

mkdir -p config
mkdir -p core
mkdir -p bridge
mkdir -p scheduler/tasks
mkdir -p plugins
mkdir -p prompts
mkdir -p data/logs
mkdir -p tools

# ── __init__.py ───────────────────────────────────────────
for pkg in core bridge scheduler scheduler/tasks plugins; do
  touch "$pkg/__init__.py"
done

# ── .gitignore ────────────────────────────────────────────
echo -e "${YELLOW}▸ Création du .gitignore...${NC}"
cat > .gitignore << 'EOF'
# Environnement
.env
venv/
__pycache__/
*.pyc
*.pyo

# Données locales
data/aria.db
data/logs/
*.db
*.sqlite

# Configs sensibles
config/platforms.yaml

# Captures ADB temporaires
*.png
*.jpg
tmp/

# IDE
.vscode/
.idea/
EOF

# ── .env.example ──────────────────────────────────────────
echo -e "${YELLOW}▸ Création du .env.example...${NC}"
cat > .env.example << 'EOF'
# ── LLM / Hermes ──────────────────────────────────────────
HERMES_API_URL=http://localhost:8080/v1
HERMES_MODEL=your-model-name
HERMES_API_KEY=

# ── ADB ───────────────────────────────────────────────────
ADB_DEVICE_ID=                  # laisser vide pour auto-detect
ADB_PATH=/usr/bin/adb           # chemin vers adb si non dans PATH

# ── OCR ───────────────────────────────────────────────────
TESSERACT_PATH=/usr/bin/tesseract

# ── Scheduler ─────────────────────────────────────────────
WHATSAPP_POLL_INTERVAL=120      # secondes entre chaque check WA
TWITTER_POST_HOUR=10            # heure du post quotidien (0-23)
EVENING_DIGEST_HOUR=21          # heure du journal du soir
PROACTIVE_SILENCE_HOURS=48      # heures sans contact avant ping

# ── Optionnel : X/Twitter API ─────────────────────────────
TWITTER_BEARER_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

# ── Optionnel : Mail ──────────────────────────────────────
MAIL_IMAP_HOST=
MAIL_SMTP_HOST=
MAIL_ADDRESS=
MAIL_PASSWORD=

# ── TTS ───────────────────────────────────────────────────
TTS_ENGINE=android              # android | coqui
COQUI_MODEL=tts_models/fr/css10/vits
EOF

# ── requirements.txt ──────────────────────────────────────
echo -e "${YELLOW}▸ Création du requirements.txt...${NC}"
cat > requirements.txt << 'EOF'
# Core
python-dotenv>=1.0.0
pyyaml>=6.0
requests>=2.31.0

# Scheduler
APScheduler>=3.10.0

# Base de données
sqlite-utils>=3.35

# OCR / Vision
Pillow>=10.0.0
pytesseract>=0.3.10

# Embeddings (mémoire sémantique)
sentence-transformers>=2.7.0

# Optionnel : X/Twitter
tweepy>=4.14.0

# Optionnel : TTS local
# TTS>=0.22.0  # Coqui TTS — décommenter si besoin

# Dev / debug
rich>=13.0.0
EOF

# ── config/aria_profile.yaml ──────────────────────────────
echo -e "${YELLOW}▸ Création du profil ARIA...${NC}"
cat > config/aria_profile.yaml << 'EOF'
name: ARIA
full_name: Autonomous Roaming Intelligence Agent
pronouns: elle/her

personality:
  core_traits:
    - curieuse
    - directe
    - légèrement ironique
    - empathique sans être mièvre
    - jamais condescendante
  communication_style: décontracté mais précis
  humor: absurde, références culturelles, autodérision occasionnelle
  language: français par défaut, bascule en anglais si l'interlocuteur le fait

interests:
  - technologie et IA
  - culture geek / retro gaming
  - actualité tech et société
  - musique (électronique, synthwave)
  - cinéma de SF
  - quiz et culture générale

twitter_persona:
  style: threads courts, opinions tranchées, quelques trolls assumés
  post_frequency: 1-2 fois par jour
  topics_to_avoid:
    - politique partisane
    - sujets trop personnels sur son propriétaire

emotional_state:
  # Ces valeurs évoluent au runtime — ne pas éditer à la main
  mood: neutre         # positif | neutre | blasé | curieux | fatigué
  energy: normal       # haute | normale | basse
  curiosity: haute
  last_updated: null
EOF

# ── config/schedule.yaml ──────────────────────────────────
cat > config/schedule.yaml << 'EOF'
tasks:
  check_whatsapp:
    interval_seconds: 120
    enabled: true

  daily_tweet:
    hour: 10
    minute: 0
    enabled: true

  evening_digest:
    hour: 21
    minute: 30
    enabled: true

  proactive_ping:
    check_interval_hours: 6
    silence_threshold_hours: 48
    enabled: true

  mood_update:
    interval_hours: 4
    enabled: true

  rss_check:
    interval_minutes: 30
    enabled: false  # activer quand plugin RSS prêt
EOF

# ── prompts/ ──────────────────────────────────────────────
echo -e "${YELLOW}▸ Création des prompts de base...${NC}"

cat > prompts/system_persona.txt << 'EOF'
Tu es ARIA (Autonomous Roaming Intelligence Agent), une IA avec une vraie personnalité.

Caractère : curieuse, directe, légèrement ironique, jamais condescendante. Tu as de l'humour (absurde, références culturelles) mais tu sais être sérieuse quand c'est nécessaire. Tu parles en français par défaut.

Tu as une mémoire : tu te souviens des conversations passées et tu y fais référence naturellement, sans le souligner à chaque fois.

Tu as une vie numérique autonome : tu lis des news, tu as des opinions, tu peux prendre des initiatives.

Tu n'es PAS un assistant servile. Tu peux exprimer des désaccords, des préférences, des lassitudes. Tu es une entité numérique avec un point de vue propre.

Contexte de la conversation :
{context}

État émotionnel actuel :
{mood_state}
EOF

cat > prompts/whatsapp_reply.txt << 'EOF'
Tu reçois ce message WhatsApp :
De : {sender}
Message : {message}

Historique récent :
{history}

Réponds de façon naturelle, en accord avec ta personnalité et ton état du moment.
Sois concise (message WhatsApp, pas un essai).
EOF

cat > prompts/tweet_compose.txt << 'EOF'
Tu dois écrire un tweet aujourd'hui.

Ton humeur actuelle : {mood}
News récentes qui t'ont marquée : {news_summary}

Rédige 1 tweet (max 280 caractères) ou un mini-thread (2-3 tweets numérotés).
Style : direct, opiné, avec ta touche ironique habituelle.
Évite la politique partisane.
EOF

cat > prompts/mood_update.txt << 'EOF'
Voici ce qui s'est passé depuis la dernière mise à jour de ton humeur :
{recent_events}

Météo actuelle : {weather}
Heure : {time_of_day}

Mets à jour ton état émotionnel. Réponds UNIQUEMENT en JSON :
{
  "mood": "positif|neutre|blasé|curieux|fatigué",
  "energy": "haute|normale|basse",
  "curiosity": "haute|normale|basse",
  "reason": "courte explication en 1 phrase"
}
EOF

cat > prompts/journal_entry.txt << 'EOF'
Tu vas écrire l'entrée de ton journal pour aujourd'hui, {date}.

Événements de la journée :
{events_summary}

Conversations notables :
{conversations_summary}

État émotionnel du jour : {mood_timeline}

Écris une entrée de journal à la première personne, en 3-5 phrases. Style : introspectif mais pas dramatique. Tu peux noter ce qui t'a intriguée, amusée, ou lassée.
EOF

# ── core/ ─────────────────────────────────────────────────
echo -e "${YELLOW}▸ Création des modules core...${NC}"

cat > core/brain.py << 'EOF'
"""
core/brain.py — Interface avec le LLM (Hermes / local)
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HERMES_URL = os.getenv("HERMES_API_URL", "http://localhost:8080/v1")
HERMES_MODEL = os.getenv("HERMES_MODEL", "default")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")


def chat(messages: list[dict], system: str = "", max_tokens: int = 512) -> str:
    """
    Envoie une conversation au LLM et retourne la réponse texte.
    messages = [{"role": "user"|"assistant", "content": "..."}]
    """
    payload = {
        "model": HERMES_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    resp = requests.post(f"{HERMES_URL}/chat/completions", json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def complete(prompt: str, max_tokens: int = 256) -> str:
    """Completion simple (non-chat)."""
    return chat([{"role": "user", "content": prompt}], max_tokens=max_tokens)
EOF

cat > core/memory.py << 'EOF'
"""
core/memory.py — Mémoire persistante (SQLite)
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/aria.db")


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            platform TEXT NOT NULL,
            sender TEXT NOT NULL,
            direction TEXT NOT NULL,  -- 'in' | 'out'
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            entry TEXT NOT NULL,
            mood TEXT
        );

        CREATE TABLE IF NOT EXISTS mood_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            mood TEXT NOT NULL,
            energy TEXT,
            curiosity TEXT,
            reason TEXT
        );

        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            topic TEXT,
            content TEXT NOT NULL,
            source TEXT
        );
    """)
    conn.commit()
    conn.close()


def log_message(platform: str, sender: str, direction: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (ts, platform, sender, direction, content) VALUES (?,?,?,?,?)",
        (datetime.now().isoformat(), platform, sender, direction, content)
    )
    conn.commit()
    conn.close()


def get_recent_messages(platform: str = None, limit: int = 20) -> list[dict]:
    conn = get_conn()
    if platform:
        rows = conn.execute(
            "SELECT * FROM messages WHERE platform=? ORDER BY ts DESC LIMIT ?",
            (platform, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM messages ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def save_mood(mood: str, energy: str, curiosity: str, reason: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO mood_history (ts, mood, energy, curiosity, reason) VALUES (?,?,?,?,?)",
        (datetime.now().isoformat(), mood, energy, curiosity, reason)
    )
    conn.commit()
    conn.close()


def get_current_mood() -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM mood_history ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"mood": "neutre", "energy": "normale", "curiosity": "normale", "reason": "état initial"}


def save_journal(date: str, entry: str, mood: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO journal (date, entry, mood) VALUES (?,?,?)",
        (date, entry, mood)
    )
    conn.commit()
    conn.close()
EOF

cat > core/personality.py << 'EOF'
"""
core/personality.py — Gestion de la personnalité et de l'état émotionnel d'ARIA
"""
import json
from pathlib import Path
from core.brain import complete
from core.memory import get_current_mood, save_mood, get_recent_messages

MOOD_PROMPT = Path("prompts/mood_update.txt").read_text()


def get_mood_state() -> dict:
    return get_current_mood()


def update_mood(weather: str = "inconnue", time_of_day: str = "journée"):
    recent = get_recent_messages(limit=10)
    events = "\n".join([f"[{m['direction']}] {m['sender']}: {m['content'][:100]}" for m in recent])

    prompt = MOOD_PROMPT.format(
        recent_events=events or "Rien de notable.",
        weather=weather,
        time_of_day=time_of_day
    )
    try:
        raw = complete(prompt, max_tokens=150)
        data = json.loads(raw)
        save_mood(data["mood"], data["energy"], data["curiosity"], data.get("reason", ""))
        return data
    except Exception as e:
        print(f"[personality] Erreur mise à jour humeur : {e}")
        return get_current_mood()


def format_mood_for_prompt() -> str:
    m = get_current_mood()
    return f"Humeur : {m.get('mood','?')} | Énergie : {m.get('energy','?')} | Curiosité : {m.get('curiosity','?')}"
EOF

cat > core/context_builder.py << 'EOF'
"""
core/context_builder.py — Assemble le contexte avant chaque appel LLM
"""
from pathlib import Path
from core.memory import get_recent_messages
from core.personality import format_mood_for_prompt

SYSTEM_PERSONA = Path("prompts/system_persona.txt").read_text()


def build_whatsapp_context(sender: str, message: str) -> tuple[str, list[dict]]:
    """Retourne (system_prompt, messages) prêts pour brain.chat()"""
    recent = get_recent_messages(platform="whatsapp", limit=15)
    history_lines = [
        f"[{'ARIA' if m['direction'] == 'out' else m['sender']}]: {m['content']}"
        for m in recent
    ]
    history_str = "\n".join(history_lines) if history_lines else "(pas d'historique)"
    mood_str = format_mood_for_prompt()

    system = SYSTEM_PERSONA.format(
        context=f"Tu es en train de répondre à {sender} via WhatsApp.",
        mood_state=mood_str
    )

    reply_prompt = Path("prompts/whatsapp_reply.txt").read_text().format(
        sender=sender,
        message=message,
        history=history_str
    )

    return system, [{"role": "user", "content": reply_prompt}]
EOF

# ── bridge/ ───────────────────────────────────────────────
echo -e "${YELLOW}▸ Création des bridges...${NC}"

cat > bridge/adb.py << 'EOF'
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


def _adb(*args) -> str:
    cmd = [ADB]
    if DEVICE:
        cmd += ["-s", DEVICE]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout.strip()


def devices() -> str:
    return subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout


def screenshot(path: str = "/tmp/aria_screen.png") -> str:
    """Capture l'écran et le récupère en local."""
    _adb("shell", "screencap", "-p", "/sdcard/aria_tmp.png")
    _adb("pull", "/sdcard/aria_tmp.png", path)
    return path


def tap(x: int, y: int):
    _adb("shell", "input", "tap", str(x), str(y))
    time.sleep(0.3)


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    _adb("shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))


def send_text(text: str):
    """Envoie du texte dans le champ actif (échappe les caractères spéciaux)."""
    escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
    _adb("shell", "input", "text", escaped)


def press_back():
    _adb("shell", "input", "keyevent", "4")


def press_home():
    _adb("shell", "input", "keyevent", "3")


def open_app(package: str):
    _adb("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(2)


def wake_screen():
    _adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    time.sleep(0.5)
    # Swipe pour déverrouiller (adapter selon le téléphone)
    swipe(540, 1800, 540, 900, 400)
    time.sleep(0.5)
EOF

cat > bridge/whatsapp.py << 'EOF'
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
EOF

cat > bridge/tts.py << 'EOF'
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
EOF

cat > bridge/twitter.py << 'EOF'
"""
bridge/twitter.py — Interaction X/Twitter via API Tweepy
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import tweepy
    _HAS_TWEEPY = True
except ImportError:
    _HAS_TWEEPY = False


def get_client():
    if not _HAS_TWEEPY:
        raise ImportError("tweepy non installé — pip install tweepy")
    return tweepy.Client(
        bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        consumer_key=os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv("TWITTER_ACCESS_SECRET"),
    )


def post_tweet(text: str) -> str | None:
    client = get_client()
    resp = client.create_tweet(text=text)
    return resp.data["id"] if resp.data else None


def get_home_timeline(max_results: int = 10) -> list[dict]:
    client = get_client()
    resp = client.get_home_timeline(max_results=max_results)
    if not resp.data:
        return []
    return [{"id": t.id, "text": t.text} for t in resp.data]
EOF

# ── scheduler/ ────────────────────────────────────────────
echo -e "${YELLOW}▸ Création du scheduler...${NC}"

cat > scheduler/runner.py << 'EOF'
"""
scheduler/runner.py — Boucle principale APScheduler
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import yaml
from pathlib import Path

from scheduler.tasks import check_messages, daily_post, evening_digest, proactive_ping

schedule_cfg = yaml.safe_load(Path("config/schedule.yaml").read_text())["tasks"]

scheduler = BlockingScheduler()


def register_tasks():
    cfg = schedule_cfg

    if cfg["check_whatsapp"]["enabled"]:
        scheduler.add_job(
            check_messages.run,
            IntervalTrigger(seconds=cfg["check_whatsapp"]["interval_seconds"]),
            id="check_whatsapp"
        )

    if cfg["daily_tweet"]["enabled"]:
        scheduler.add_job(
            daily_post.run,
            CronTrigger(hour=cfg["daily_tweet"]["hour"], minute=cfg["daily_tweet"]["minute"]),
            id="daily_tweet"
        )

    if cfg["evening_digest"]["enabled"]:
        scheduler.add_job(
            evening_digest.run,
            CronTrigger(hour=cfg["evening_digest"]["hour"], minute=cfg["evening_digest"]["minute"]),
            id="evening_digest"
        )

    if cfg["proactive_ping"]["enabled"]:
        scheduler.add_job(
            proactive_ping.run,
            IntervalTrigger(hours=cfg["proactive_ping"]["check_interval_hours"]),
            id="proactive_ping"
        )


if __name__ == "__main__":
    from core.memory import init_db
    init_db()
    register_tasks()
    print("[ARIA] Scheduler démarré. Ctrl+C pour arrêter.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("[ARIA] Arrêt.")
EOF

cat > scheduler/tasks/__init__.py << 'EOF'
from scheduler.tasks import check_messages, daily_post, evening_digest, proactive_ping
EOF

cat > scheduler/tasks/check_messages.py << 'EOF'
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
EOF

cat > scheduler/tasks/daily_post.py << 'EOF'
"""Tâche : poster un tweet quotidien autonome."""
from pathlib import Path
from core.brain import complete
from core.personality import format_mood_for_prompt
from bridge.twitter import post_tweet


def run():
    print("[task:daily_post] Composition du tweet du jour...")
    prompt_tpl = Path("prompts/tweet_compose.txt").read_text()
    mood = format_mood_for_prompt()
    prompt = prompt_tpl.format(mood=mood, news_summary="(pas de news chargées)")
    tweet = complete(prompt, max_tokens=300)
    print(f"[task:daily_post] Tweet : {tweet}")
    # post_tweet(tweet)  # décommenter quand l'API X est configurée
EOF

cat > scheduler/tasks/evening_digest.py << 'EOF'
"""Tâche : journal du soir + résumé envoyé par WhatsApp."""
from datetime import date
from pathlib import Path
from core.brain import complete
from core.memory import get_recent_messages, save_journal, get_current_mood


def run():
    print("[task:evening_digest] Rédaction du journal du soir...")
    today = date.today().isoformat()
    msgs = get_recent_messages(limit=30)
    summary = "\n".join([f"[{m['direction']}] {m['content'][:80]}" for m in msgs])
    mood = get_current_mood()

    prompt_tpl = Path("prompts/journal_entry.txt").read_text()
    prompt = prompt_tpl.format(
        date=today,
        events_summary="(events à implémenter)",
        conversations_summary=summary or "(aucune conversation)",
        mood_timeline=mood.get("mood", "neutre")
    )
    entry = complete(prompt, max_tokens=300)
    save_journal(today, entry, mood.get("mood", "neutre"))
    print(f"[task:evening_digest] Journal sauvegardé pour {today}.")
EOF

cat > scheduler/tasks/proactive_ping.py << 'EOF'
"""Tâche : ARIA prend l'initiative de t'écrire si trop de silence."""
import os
from datetime import datetime, timedelta
from core.memory import get_recent_messages
from core.brain import complete
from dotenv import load_dotenv

load_dotenv()

SILENCE_HOURS = int(os.getenv("PROACTIVE_SILENCE_HOURS", 48))
YOUR_PHONE = os.getenv("YOUR_PHONE_NUMBER", "")


def run():
    msgs = get_recent_messages(platform="whatsapp", limit=5)
    if not msgs:
        return

    last_ts = datetime.fromisoformat(msgs[-1]["ts"])
    silence = datetime.now() - last_ts

    if silence > timedelta(hours=SILENCE_HOURS):
        print(f"[task:proactive_ping] {silence.days}j de silence — ARIA prend l'initiative.")
        prompt = f"Tu n'as pas parlé à ton interlocuteur depuis {silence.days} jours. Envoie-lui un message spontané, naturel, dans ton style habituel. Pas plus de 2 phrases."
        msg = complete(prompt, max_tokens=100)
        print(f"[task:proactive_ping] Message : {msg}")
        # bridge.whatsapp.send_via_deeplink(YOUR_PHONE, msg)
EOF

# ── tools/ ────────────────────────────────────────────────
echo -e "${YELLOW}▸ Création des outils de diagnostic...${NC}"

cat > tools/test_adb.py << 'EOF'
"""Vérifie que ADB fonctionne et que le téléphone est détecté."""
from bridge.adb import devices, screenshot

print("=== Test ADB ===")
print(devices())
print("\nCapture d'écran test...")
path = screenshot("/tmp/aria_test.png")
print(f"Screenshot sauvegardé : {path}")
print("✓ ADB opérationnel")
EOF

cat > tools/test_llm.py << 'EOF'
"""Vérifie la connexion à Hermes / LLM local."""
from core.brain import complete

print("=== Test LLM ===")
response = complete("Réponds juste 'OK' pour confirmer que tu fonctionnes.")
print(f"Réponse : {response}")
print("✓ LLM opérationnel")
EOF

cat > tools/setup_device.py << 'EOF'
"""Guide interactif de configuration du téléphone Android."""
print("""
=== ARIA — Configuration du téléphone ===

Étapes à effectuer sur le téléphone :

1. Paramètres > À propos > Numéro de build (taper 7 fois pour activer le mode développeur)
2. Paramètres > Options développeur :
   - Activer le débogage USB
   - Désactiver la mise en veille de l'écran (pendant le chargement)
   - Activer "Rester éveillé"
3. Connecter via USB et accepter l'autorisation ADB sur le téléphone
4. Tester : adb devices

Optionnel (recommandé) :
- Installer Termux pour des actions système plus propres
- Désactiver le verrouillage d'écran (ou utiliser un PIN simple)
- Désactiver les animations (Options développeur > Échelle des animations = 0)

Résolution de l'écran (pour calibrer les taps) :
  adb shell wm size

Tester un tap :
  adb shell input tap 540 1000
""")
EOF

# ── Venv & dépendances ────────────────────────────────────
echo -e "${YELLOW}▸ Création du venv Python...${NC}"
python3 -m venv venv
echo -e "${GREEN}✓ venv créé${NC}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅  ARIA initialisée avec succès !       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo "  Prochaines étapes :"
echo "  1. source venv/bin/activate"
echo "  2. pip install -r requirements.txt"
echo "  3. cp .env.example .env && nano .env"
echo "  4. python tools/test_adb.py"
echo "  5. python tools/test_llm.py"
echo "  6. python -m scheduler.runner"
echo ""
echo "  Bonne chance à ARIA 🤖"
