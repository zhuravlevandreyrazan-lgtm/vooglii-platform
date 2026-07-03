from __future__ import annotations

from . import get_bot


async def error_handler(update, context):
    bot = get_bot()
    user_id = None
    command_text = ""
    role = "unknown"
    if getattr(update, "effective_user", None):
        user_id = getattr(update.effective_user, "id", None)
    if getattr(update, "message", None):
        command_text = getattr(update.message, "text", "") or ""
    if user_id is not None:
        try:
            role = bot.get_user_role(user_id)
        except Exception:
            role = "unknown"
    error_obj = getattr(context, "error", None)
    bot.logger.error(
        "Telegram command failed user_id=%s role=%s command=%s error_type=%s",
        user_id,
        role,
        bot.sanitize_log_value(command_text),
        type(error_obj).__name__ if error_obj else "UnknownError",
        exc_info=(type(error_obj), error_obj, getattr(error_obj, "__traceback__", None)) if error_obj else None,
    )
    if getattr(update, "message", None):
        await update.message.reply_text(
            "Команда временно не выполнилась.\n\nЯ уже зафиксировал ошибку в диагностике. Попробуйте повторить позже."
        )
