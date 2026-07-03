from __future__ import annotations

import importlib
import sys
from pathlib import Path

from telegram.ext import Application, CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters

from .registry import _command_handlers
from .runtime.error_handler import error_handler
from .runtime.heartbeat import mark_runtime_health
from .runtime.jobs import attach_application, register_background_jobs
from .runtime.logging import configure_telegram_logging, log_polling_started, log_startup
from .runtime.permissions import wrap_command_handler


def _load_telegram_bot_module():
    main_module = sys.modules.get("__main__")
    main_file = getattr(main_module, "__file__", None)
    if main_file and Path(main_file).name == "telegram_bot.py":
        return main_module
    return importlib.import_module("telegram_bot")


def create_application():
    bot = _load_telegram_bot_module()

    configure_telegram_logging()
    bot.validate_token_encryption_configuration(require_in_production=True)
    bot.init_db()
    if not bot.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN РЅРµ Р·Р°РґР°РЅ. РЈСЃС‚Р°РЅРѕРІРёС‚Рµ environment variable BOT_TOKEN РїРµСЂРµРґ Р·Р°РїСѓСЃРєРѕРј.")

    mark_runtime_health("starting", bot.DB_NAME)
    log_startup()

    app = Application.builder().token(bot.BOT_TOKEN).build()
    attach_application(app)

    for name, handler in _command_handlers().items():
        app.add_handler(CommandHandler(name, wrap_command_handler(name, handler)))
    app.add_handler(PreCheckoutQueryHandler(bot.precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, bot.successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.buttons))
    app.add_error_handler(error_handler)

    if app.job_queue:
        register_background_jobs(app)
    return app


def main():
    app = create_application()
    mark_runtime_health("alive", "polling")
    log_polling_started()
    app.run_polling()
