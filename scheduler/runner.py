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
