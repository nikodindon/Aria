"""
core/memory.py — Mémoire persistante (SQLite)
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/aria.db")

_initialized = False


def get_conn() -> sqlite3.Connection:
    """Ouvre la connexion SQLite. Initialise le schéma au premier appel."""
    global _initialized
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if not _initialized:
        _init_db_unlocked(conn)
        _initialized = True
    return conn


def init_db():
    """Crée les tables si elles n'existent pas. Idempotent, safe à appeler au boot."""
    conn = get_conn()
    conn.commit()
    conn.close()


def _init_db_unlocked(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            platform TEXT NOT NULL,
            sender TEXT NOT NULL,
            direction TEXT NOT NULL,
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

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL UNIQUE,
            name TEXT,
            paired_at TEXT NOT NULL,
            last_seen TEXT,
            notes TEXT
        );
    """)
    conn.commit()


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


# --- users (Phase 2 : gateway pairing) -----------------------------------

def pair_user(phone: str, name: str = None, notes: str = None) -> int:
    """Enregistre un user dans la DB, ou met a jour si deja existant.

    Retourne l'ID de la ligne creee ou mise a jour.
    """
    from datetime import datetime
    conn = get_conn()
    now = datetime.now().isoformat()
    # Normalise le num : on garde uniquement les chiffres
    digits = "".join(c for c in phone if c.isdigit())
    conn.execute(
        """INSERT INTO users (phone, name, paired_at, last_seen, notes)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(phone) DO UPDATE SET
             name=COALESCE(excluded.name, users.name),
             notes=COALESCE(excluded.notes, users.notes)""",
        (digits, name, now, now, notes)
    )
    conn.commit()
    # Recupere l'ID
    row = conn.execute("SELECT id FROM users WHERE phone=?", (digits,)).fetchone()
    conn.close()
    return int(row["id"]) if row else -1


def get_user_by_phone(phone: str) -> dict | None:
    """Retourne le user avec ce num, ou None si pas trouve."""
    digits = "".join(c for c in phone if c.isdigit())
    # Match sur les 9 derniers chiffres (flexibilite sur le prefixe pays)
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    for r in rows:
        u = dict(r)
        if u["phone"][-9:] == digits[-9:]:
            return u
    return None


def touch_user(user_id: int):
    """Met a jour last_seen a maintenant."""
    from datetime import datetime
    conn = get_conn()
    conn.execute(
        "UPDATE users SET last_seen=? WHERE id=?",
        (datetime.now().isoformat(), user_id)
    )
    conn.commit()
    conn.close()


def list_users() -> list[dict]:
    """Liste tous les users enregistres."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY last_seen DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
