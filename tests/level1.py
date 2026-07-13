"""
tests/level1.py — Suite de tests Level 1 pour ARIA.

Couvre 23 tests : unitaires, integration, securite, regression.
Tous automatises (pas besoin d'envoyer un message WhatsApp).

Usage :
  ./venv/bin/python3 tests/level1.py

Cible :
  - core/memory.py : redact_credentials, get_user_by_phone,
    recall_relevant, schema stability, no-credential-leak
  - tools/aria_loop.py : parse_whatsapp_notifications,
    extract_phone_from_title
  - plugins/weather.py : get_weather, fallback gracieux
  - plugins/reminder.py : add/list/mark_done round-trip
  - core/context_builder.py : build_whatsapp_context sections
  - bridge/whatsapp.py : list_conversations guard
  - bridge/whatsapp.py : current_view (live, returns valid enum)
  - tools/aria_plugins.py : CLI subcommands
  - Security : no credential leak, no secret in tracked files
  - Regression : DB schema stable
"""
import re
import subprocess
import sys
import tempfile
import os
from pathlib import Path

ARIA = Path(__file__).resolve().parent.parent
VENV_PY = ARIA / "venv" / "bin" / "python3"

failures = []
passed = 0


def check(name, ok, detail=""):
    """Affiche le resultat et accumule."""
    global passed
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failures.append(name)


def run_python(code: str, timeout: int = 30) -> tuple[bool, str, str]:
    """Execute un bout de code Python dans le venv ARIA."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False,
        prefix="hermes-verify-aria-l1-",
    ) as f:
        f.write(code)
        tmp = f.name
    try:
        proc = subprocess.run(
            [str(VENV_PY), tmp], capture_output=True, text=True,
            timeout=timeout, cwd=str(ARIA),
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"timeout after {timeout}s"
    finally:
        os.unlink(tmp)


# === UNIT TESTS ===

print("=== UNIT TESTS ===")

# T1. redact_credentials
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from bridge.whatsapp import redact_credentials
r = redact_credentials("Votre code est 078786")
assert "[REDACTED]" in r, f"expected [REDACTED] in {r!r}"
r = redact_credentials("Tel 0612345678")
assert "[REDACTED]" not in r, f"10 digits should not be redacted: {r!r}"
assert redact_credentials("Aucun chiffre ici") == "Aucun chiffre ici"
print("OK")
''')
check("T1 redact_credentials (codes 4-8 chiffres, pas 10)", "OK" in out)

# T2. get_user_by_phone
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from core.memory import get_user_by_phone
u = get_user_by_phone("+33617186267")
assert u is not None
assert u["name"] == "Niko"
u2 = get_user_by_phone("0617186267")
assert u2 is not None and u2["id"] == u["id"]
u3 = get_user_by_phone("+33000000000")
assert u3 is None
print("OK")
''')
check("T2 get_user_by_phone (9-digit match)", "OK" in out)

# T3. recall_relevant
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from core.memory import recall_relevant
r = recall_relevant("musique", k=3)
assert len(r) >= 1
r2 = recall_relevant("Tu te rappelles de musique ?", k=3)
assert len(r2) >= 1
assert recall_relevant("", k=3) == []
print("OK")
''')
check("T3 recall_relevant (sanitize + OR + empty)", "OK" in out)

# T4. parse_whatsapp_notifications
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from tools.aria_loop import parse_whatsapp_notifications
mock = """NotificationRecord(0x0b03713c: pkg=com.whatsapp user=UserHandle{0} key=0|com.whatsapp|10000|null|10275:
  extras={
    android.title=String (WhatsApp : +33 6 17 18 62 67)
    android.text=String (Test msg)
  }
)
"""
notifs = parse_whatsapp_notifications(mock)
assert len(notifs) == 1
assert notifs[0]["title"] == "WhatsApp : +33 6 17 18 62 67"
assert notifs[0]["text"] == "Test msg"
mock2 = "NotificationRecord(0x0b03713c: pkg=com.facebook.orca key=foo"
assert parse_whatsapp_notifications(mock2) == []
print("OK")
''')
check("T4 parse_whatsapp_notifications", "OK" in out, f"err={err[:200] if err else ''}")

# T5. extract_phone_from_title
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from tools.aria_loop import extract_phone_from_title
assert extract_phone_from_title("WhatsApp : +33 6 17 18 62 67") == "33617186267"
assert extract_phone_from_title("WhatsApp : 06 17 18 62 67") == "0617186267"
assert extract_phone_from_title("WhatsApp : Niko") is None
print("OK")
''')
check("T5 extract_phone_from_title", "OK" in out)

# T6. reminder round-trip
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from plugins.reminder import add_reminder, list_reminders, mark_done
rid = add_reminder("test", due_at="2026-12-31T18:00:00")
assert rid > 0
assert any(r["id"] == rid for r in list_reminders())
assert mark_done(rid)
assert not any(r["id"] == rid for r in list_reminders())
assert any(r["id"] == rid and r["done"] for r in list_reminders(include_done=True))
print("OK")
''')
check("T6 reminder round-trip", "OK" in out)

# T7. weather
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from plugins.weather import get_weather
w = get_weather("Paris")
assert "temp_c" in w
w2 = get_weather("VilleInexistanteXYZ12345")
assert w2["temp_c"] is None
assert w2["description"] == "(indisponible)"
print("OK")
''')
check("T7 get_weather (Paris + fallback gracieux)", "OK" in out)

# T8. current_view
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from bridge.whatsapp import current_view
v = current_view()
assert v in ("discussions", "conversation", "other"), f"unexpected: {v!r}"
print(f"OK view={v!r}")
''')
check("T8 current_view (returns valid enum)", "OK" in out)


# === INTEGRATION TESTS ===

print()
print("=== INTEGRATION TESTS ===")

# T9. aria_loop --once
proc = subprocess.run(
    [str(VENV_PY), str(ARIA / "tools" / "aria_loop.py"), "--once"],
    capture_output=True, text=True, timeout=60, cwd=str(ARIA),
)
out = proc.stdout + proc.stderr
check("T9 aria_loop --once (idle)", proc.returncode == 0 and "ARIA loop gateway" in out)

# T10. news end-to-end
proc = subprocess.run(
    [str(VENV_PY), str(ARIA / "tools" / "aria_plugins.py"), "news", "--limit", "3", "--no-fetch"],
    capture_output=True, text=True, timeout=30, cwd=str(ARIA),
)
check("T10 aria_plugins news end-to-end", proc.returncode == 0 and "[hackernews]" in proc.stdout)

# T11. weather end-to-end
proc = subprocess.run(
    [str(VENV_PY), str(ARIA / "tools" / "aria_plugins.py"), "weather", "Paris"],
    capture_output=True, text=True, timeout=30, cwd=str(ARIA),
)
check("T11 aria_plugins weather end-to-end", proc.returncode == 0 and "Paris" in proc.stdout)

# T12. evening_digest mock
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
import scheduler.tasks.evening_digest as ed
calls = []
def mock_send(text, phone=None, screenshot_path=None):
    calls.append({"text": text, "phone": phone})
    return True
ed.send_message = mock_send
ed.run()
assert len(calls) == 1
assert calls[0]["phone"] == "33617186267"
print("OK")
''')
check("T12 evening_digest.run() mocked", "OK" in out)

# T13. proactive_ping skip
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
import scheduler.tasks.proactive_ping as pp
calls = []
def mock_send(text, phone=None, screenshot_path=None):
    calls.append(1)
    return True
pp.send_message = mock_send
pp.run()
assert len(calls) == 0
print("OK")
''')
check("T13 proactive_ping.run() silent", "OK" in out)

# T15. list_conversations guard
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from bridge.whatsapp import list_conversations
convs = list_conversations()
assert convs == [], f"guard failed: got {len(convs)}"
print("OK")
''')
check("T15 list_conversations guard (in conv view)", "OK" in out)

# T17. build_whatsapp_context
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from core.context_builder import build_whatsapp_context
system, messages = build_whatsapp_context("Niko", "Salut")
content = messages[0]["content"]
for section in ["Historique récent", "Messages passés", "news lues", "Météo"]:
    assert section in content
assert "ARIA" in system
print("OK")
''')
check("T17 build_whatsapp_context (4 sections + persona)", "OK" in out)


# === ROBUSTESSE ===

print()
print("=== ROBUSTESSE ===")

# T24. Notif num non appaire
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
import tools.aria_loop as al
def fake_dump():
    return """NotificationRecord(0x0b03713c: pkg=com.whatsapp user=UserHandle{0} key=0|com.whatsapp|10000|null|99999:
  extras={
    android.title=String (WhatsApp : +33 6 00 00 00 00)
    android.text=String (Bidon)
  }
)
"""
al.dump_notifications = fake_dump
al.reply_to_user = lambda u, t: True
treated = al.process_pending_notifications(set())
assert treated == 0
print("OK")
''')
check("T24 notif num non appaire = skip", "OK" in out)

# T27. wttr fallback
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from plugins.weather import get_weather
w = get_weather("VilleQuiNExistePasXYZ12345")
assert w["temp_c"] is None
assert w["description"] == "(indisponible)"
print("OK")
''')
check("T27 wttr.in fallback", "OK" in out)

# T28. DB schema
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from core.memory import get_conn
conn = get_conn()
all_objs = [r[0] for r in conn.execute("SELECT name FROM sqlite_master").fetchall()]
expected = {"messages", "journal", "mood_history", "knowledge", "users", "messages_fts"}
for name in expected:
    assert name in all_objs, f"{name!r} missing from {all_objs}"
print("OK")
''')
check("T28 DB schema (5 tables + 1 FTS5)", "OK" in out)

# T30. redact_credentials 10k
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
import time
from bridge.whatsapp import redact_credentials
text = ("blabla " * 1000) + "code 123456" + (" blabla " * 1000)
t0 = time.time()
r = redact_credentials(text)
elapsed = time.time() - t0
assert "[REDACTED]" in r
assert elapsed < 2.0, f"too slow: {elapsed:.2f}s"
print(f"OK {elapsed*1000:.0f}ms")
''')
check("T30 redact_credentials 10k chars (< 2s)", "OK" in out)


# === SECURITE ===

print()
print("=== SECURITE ===")

# T31. No credential leak (post-fix)
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from core.memory import log_message, get_recent_messages, recall_relevant, rebuild_fts_index
log_message("whatsapp", "PayPal", "in", "Votre code de verification est 666222. Ne le partagez pas.")
rebuild_fts_index()
recent = get_recent_messages(platform="whatsapp", limit=10)
for m in recent:
    assert "666222" not in m["content"], f"LEAK in recent: {m[\"content\"]!r}"
hits = recall_relevant("666222 verification", k=5)
for h in hits:
    assert "666222" not in h["content"], f"LEAK in relevant: {h[\"content\"]!r}"
print("OK no leak")
''')
check("T31 no credential leak (after fix)", "OK" in out)

# T35. Code 6 chiffres redacte en milieu de phrase
ok, out, err = run_python('''
import sys
sys.path.insert(0, "/home/niko/Aria")
from bridge.whatsapp import redact_credentials
r = redact_credentials("Mon code est 456789 et il expire demain")
assert "[REDACTED]" in r
assert "456789" not in r
print("OK")
''')
check("T35 code 6 chiffres redacte en milieu de phrase", "OK" in out)

# T52. No secret in tracked files
proc = subprocess.run(
    ["git", "-C", str(ARIA), "ls-files"],
    capture_output=True, text=True,
)
all_files = proc.stdout.strip().splitlines()
leaks = []
for f in all_files:
    if not f.endswith((".py", ".md", ".txt", ".yaml", ".yml", ".sh")):
        continue
    path = ARIA / f
    if not path.exists():
        continue
    try:
        content = path.read_text()
    except UnicodeDecodeError:
        continue
    # Patterns construits dynamiquement (pas en clair dans le code)
    # pour eviter que le test ne se detecte lui-meme.
    p1 = "sk" + "-" + "mon" + "-" + "master" + "-" + "key"
    p2 = "Wxc" + "vbn48"
    for pattern in (p1, p2):
        if pattern in content:
            leaks.append((f, pattern))
check(f"T52 no secret in {len(all_files)} tracked files", not leaks, f"leaks={leaks}")


# === SUMMARY ===

print()
print("=" * 50)
total = passed + len(failures)
print(f"RESULT: {passed}/{total} passed")
if failures:
    print(f"FAILED ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("ALL PASSED")
