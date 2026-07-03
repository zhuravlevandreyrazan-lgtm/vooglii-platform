from __future__ import annotations

from . import get_bot
from .heartbeat import schedule_heartbeat
from .logging import log_background_jobs_scheduled


TELEGRAM_RUNTIME = {
    "application": None,
}


def attach_application(application):
    TELEGRAM_RUNTIME["application"] = application


def get_application():
    return TELEGRAM_RUNTIME.get("application")


def register_background_jobs(application):
    if not application or not getattr(application, "job_queue", None):
        return
    bot = get_bot()
    bot.schedule_background_jobs(application.job_queue)
    schedule_heartbeat(application.job_queue)
    log_background_jobs_scheduled()
