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
