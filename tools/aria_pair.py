"""
tools/aria_pair.py — Appairage d'un user ARIA (Phase 2 : gateway).

Usage :
  python tools/aria_pair.py --phone 336XXXXXXXX --name "TON_NOM"
  python tools/aria_pair.py --phone 06XXXXXXXX --name "TON_NOM" --notes "createur du projet"
  python tools/aria_pair.py --list

Enregistre le user dans la table `users` de la DB ARIA. Apres
appairage, ARIA reconnaitra les messages entrants de ce num comme
provenant d'un user autorise, et pourra repondre.

C'est l'equivalent d'un bot Telegram qu'on ajoute a ses contacts,
mais sans cloud : tout reste en local sur la DB SQLite.
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory import pair_user, get_user_by_phone, list_users


def main() -> int:
    parser = argparse.ArgumentParser(description="ARIA user pairing")
    parser.add_argument("--phone", help="Numero de l'user (format international ou national)")
    parser.add_argument("--name", help="Nom affiche (optionnel)")
    parser.add_argument("--notes", help="Notes (optionnel)")
    parser.add_argument("--list", action="store_true", help="Liste les users apparies")
    args = parser.parse_args()

    if args.list:
        users = list_users()
        if not users:
            print("Aucun user appaire. Utilise --phone pour en ajouter un.")
            return 0
        for u in users:
            print(f"  id={u['id']} phone={u['phone']} name={u.get('name')!r} last_seen={u.get('last_seen')}")
        return 0

    if not args.phone:
        parser.print_help()
        return 1

    if get_user_by_phone(args.phone):
        print(f"User avec phone {args.phone} deja appaire. Mise a jour...")
    else:
        print(f"Nouvel appairage...")

    uid = pair_user(args.phone, name=args.name, notes=args.notes)
    u = get_user_by_phone(args.phone)
    print(f"OK user_id={uid}")
    print(f"  phone : {u['phone']}")
    print(f"  name  : {u.get('name')!r}")
    print(f"  notes : {u.get('notes')!r}")
    print(f"  paired_at : {u['paired_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
