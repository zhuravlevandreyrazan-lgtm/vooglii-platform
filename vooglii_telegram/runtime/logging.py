from __future__ import annotations

import logging
import os
import socket

from . import get_bot


def configure_telegram_logging():
    bot = get_bot()
    bot.configure_logging()
    level_name = str(os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    logging.getLogger("httpx").setLevel(max(level, logging.WARNING))


def log_startup():
    bot = get_bot()
    bot.logger.info(
        "Starting Telegram bot app_env=%s db_name=%s bot_username=%s admin_count=%s",
        bot.APP_ENV,
        bot.DB_NAME,
        bot.BOT_USERNAME,
        len(bot.ADMIN_IDS),
    )
    try:
        bot.logger.info("api.telegram.org resolved=%s", socket.gethostbyname("api.telegram.org"))
    except Exception as exc:
        bot.logger.warning("Telegram DNS resolution failed: %s", bot.sanitize_log_value(str(exc)))


def log_polling_started():
    bot = get_bot()
    bot.logger.info("Telegram bot polling started")


def log_background_jobs_scheduled():
    bot = get_bot()
    bot.logger.info("Telegram background jobs scheduled")
