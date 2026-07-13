"""
plugins/reminder.py — Gestion de rappels par ARIA.

ARIA peut gerer des rappels simples : "rappelle-moi d'appeler
Maman demain a 18h". Stocke en DB, peut lister, peut marquer
comme complete.

Schema de la table reminders :
  - id
  - ts_created : datetime ISO
  - due_at : datetime ISO (ou NULL pour "sans date")
  - text : le rappel
  - done : 0/1
  - source : 'whatsapp' / 'cli' / etc.
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory import get_conn


def _ensure_table():
    """Cree la table reminders si pas existante."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_created TEXT NOT NULL,
            due_at TEXT,
            text TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            source TEXT
        );
    """)
    conn.commit()
    conn.close()


def add_reminder(text: str, due_at: str = None, source: str = "cli") -> int:
    """Ajoute un rappel. Retourne l'ID."""
    _ensure_table()
    conn = get_conn()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO reminders (ts_created, due_at, text, source) VALUES (?,?,?,?)",
        (now, due_at, text, source)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def list_reminders(include_done: bool = False) -> list[dict]:
    """Liste les rappels actifs (ou tous si include_done=True)."""
    _ensure_table()
    conn = get_conn()
    if include_done:
        rows = conn.execute(
            "SELECT * FROM reminders ORDER BY done ASC, due_at ASC NULLS LAST"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE done=0 "
            "ORDER BY due_at ASC NULLS LAST"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_done(reminder_id: int) -> bool:
    """Marque un rappel comme complete. Retourne True si modifie."""
    _ensure_table()
    conn = get_conn()
    cur = conn.execute(
        "UPDATE reminders SET done=1 WHERE id=? AND done=0",
        (reminder_id,)
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def delete_reminder(reminder_id: int) -> bool:
    """Supprime un rappel. Retourne True si supprime."""
    _ensure_table()
    conn = get_conn()
    cur = conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def due_reminders() -> list[dict]:
    """Retourne les rappels actifs qui sont en retard ou dus maintenant."""
    _ensure_table()
    conn = get_conn()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM reminders WHERE done=0 AND due_at IS NOT NULL AND due_at <= ?",
        (now,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    # Test round-trip
    rid = add_reminder("Appeler Maman", due_at="2026-07-14T18:00:00")
    print(f"Added reminder id={rid}")
    print("Active reminders:")
    for r in list_reminders():
        print(f"  #{r['id']} [{r['due_at']}] {r['text']}")
