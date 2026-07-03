from __future__ import annotations

from . import get_bot


def mark_runtime_health(status: str, details: str):
    bot = get_bot()
    bot.update_runtime_health("telegram-bot", status, details=details)


async def heartbeat_job(context):
    mark_runtime_health("alive", "polling")


def schedule_heartbeat(job_queue):
    if not job_queue:
        return
    job_queue.run_repeating(heartbeat_job, interval=30, first=1, name="telegram_bot_heartbeat")
