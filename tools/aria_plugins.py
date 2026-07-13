"""
tools/aria_plugins.py — CLI pour les plugins ARIA.

Usage :
  python tools/aria_plugins.py news              # fetch + list 5 news
  python tools/aria_plugins.py news --limit 20
  python tools/aria_plugins.py news --topic hackernews
  python tools/aria_plugins.py weather Paris
  python tools/aria_plugins.py reminder add "Appeler Maman"
  python tools/aria_plugins.py reminder list
  python tools/aria_plugins.py reminder done 1
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plugins import rss_watcher, weather, reminder


def main() -> int:
    parser = argparse.ArgumentParser(description="ARIA plugins CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # news
    p_news = sub.add_parser("news", help="RSS: fetch + list")
    p_news.add_argument("--limit", type=int, default=5)
    p_news.add_argument("--topic", help="Filtrer par topic (hackernews, ...)")
    p_news.add_argument("--no-fetch", action="store_true",
                        help="Ne pas refetch, juste lister")

    # weather
    p_weather = sub.add_parser("weather", help="Meteo locale")
    p_weather.add_argument("city", nargs="?", default="Paris")

    # reminder
    p_rem = sub.add_parser("reminder", help="Gestion des rappels")
    rem_sub = p_rem.add_subparsers(dest="rem_cmd", required=True)
    p_rem_add = rem_sub.add_parser("add", help="Ajouter un rappel")
    p_rem_add.add_argument("text")
    p_rem_add.add_argument("--due", help="Date ISO (ex: 2026-07-14T18:00:00)")
    p_rem_add.add_argument("--source", default="cli")
    p_rem_list = rem_sub.add_parser("list", help="Lister les rappels actifs")
    p_rem_list.add_argument("--all", action="store_true",
                            help="Inclure les rappels complets")
    p_rem_done = rem_sub.add_parser("done", help="Marquer comme complete")
    p_rem_done.add_argument("id", type=int)
    p_rem_del = rem_sub.add_parser("delete", help="Supprimer un rappel")
    p_rem_del.add_argument("id", type=int)

    args = parser.parse_args()

    if args.cmd == "news":
        if not args.no_fetch:
            print("=== Fetch RSS ===")
            rss_watcher.fetch_all()
        print(f"=== {args.limit} dernieres news"
              + (f' (topic={args.topic})' if args.topic else '') + " ===")
        for item in rss_watcher.get_recent_news(limit=args.limit, topic=args.topic):
            print(f"  [{item['topic']}] {item['content'][:90]}")
        return 0

    if args.cmd == "weather":
        w = weather.get_weather(args.city)
        print(f"{args.city} : {w['temp_c']}°C, {w['description']}")
        print(weather.weather_for_prompt(args.city))
        return 0

    if args.cmd == "reminder":
        if args.rem_cmd == "add":
            rid = reminder.add_reminder(args.text, due_at=args.due, source=args.source)
            print(f"OK rappel #{rid} ajoute")
            return 0
        if args.rem_cmd == "list":
            for r in reminder.list_reminders(include_done=args.all):
                status = "DONE" if r["done"] else "ACTIVE"
                due = r["due_at"] or "no date"
                print(f"  #{r['id']} [{status}] {due}  {r['text']}")
            return 0
        if args.rem_cmd == "done":
            if reminder.mark_done(args.id):
                print(f"OK rappel #{args.id} marque comme complete")
            else:
                print(f"Rappel #{args.id} pas trouve ou deja complete")
            return 1
        if args.rem_cmd == "delete":
            if reminder.delete_reminder(args.id):
                print(f"OK rappel #{args.id} supprime")
            else:
                print(f"Rappel #{args.id} pas trouve")
            return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
