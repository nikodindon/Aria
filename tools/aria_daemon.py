"""
tools/aria_daemon.py — Lance aria_loop en daemon avec auto-restart.

Fait tourner aria_loop en boucle, et si le process crash, le
relance automatiquement. C'est la version "production" du
loop, celle qu'on laisse tourner 24/7.

Usage :
  python tools/aria_daemon.py                    # en foreground
  python tools/aria_daemon.py --interval 10     # poll toutes les 10s
  nohup python tools/aria_daemon.py --interval 30 &  # en background

Ou pour systemd (Linux) :
  Voir tools/aria.service.example

KISS : on wrap le loop dans un try/except + while True qui
relance apres N secondes en cas de crash. Pas de libs externes
(daemon, supervisor, etc.), juste stdlib.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

# Dossier du projet (parent de tools/)
ARIA_DIR = Path(__file__).resolve().parent.parent
LOOP_CMD = [sys.executable, str(ARIA_DIR / "tools" / "aria_loop.py")]
RESTART_DELAY = 5  # secondes entre 2 lancements en cas de crash


def main() -> int:
    parser = argparse.ArgumentParser(description="ARIA daemon (auto-restart loop)")
    parser.add_argument("--interval", type=int, default=30,
                        help="Intervalle entre polls (defaut 30s)")
    parser.add_argument("--max-restarts", type=int, default=0,
                        help="Max restarts (0 = infini, defaut)")
    args = parser.parse_args()

    print(f"=== ARIA daemon (interval={args.interval}s) ===")
    print(f"Loop command: {' '.join(LOOP_CMD)}")
    print(f"Working dir : {ARIA_DIR}")
    print(f"Max restarts: {'infini' if args.max_restarts == 0 else args.max_restarts}")
    print(f"Ctrl+C pour arreter proprement")
    print()

    restarts = 0
    while True:
        try:
            print(f"[daemon] Lancement aria_loop (run #{restarts + 1})...")
            proc = subprocess.run(
                LOOP_CMD + ["--interval", str(args.interval)],
                cwd=str(ARIA_DIR),
            )
            print(f"[daemon] aria_loop termine avec code {proc.returncode}")
        except KeyboardInterrupt:
            print("\n[daemon] Arrete par l'utilisateur")
            return 0
        except Exception as e:
            print(f"[daemon] Exception : {e}")

        restarts += 1
        if args.max_restarts and restarts > args.max_restarts:
            print(f"[daemon] Max restarts ({args.max_restarts}) atteint, abandon")
            return 1

        print(f"[daemon] Restart dans {RESTART_DELAY}s...")
        time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    sys.exit(main())
