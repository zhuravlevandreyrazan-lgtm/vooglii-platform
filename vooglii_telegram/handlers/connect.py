from __future__ import annotations

from security.audit_log import log_privileged_action
from security.permissions import get_user_role
from vooglii_telegram.services.account_service import connect_wb_account, disconnect_wb_account

from ._bot import get_bot


async def connect_command(update, context):
    bot = get_bot()
    if not context.args:
        await update.message.reply_text(bot.connect_intro_text())
        return
    user_id = bot.uid(update)
    try:
        connect_wb_account(user_id, bot.uname(update), context.args[0].strip())
    except Exception:
        await update.message.reply_text(
            "⚠ Не удалось подключить кабинет WB.\n\n"
            "Проверьте, что API-ключ скопирован полностью, и повторите команду /connect."
        )
        return
    bot.ensure_sync_status_rows(user_id)
    if context.application and context.application.job_queue:
        bot.schedule_initial_sync(context.application.job_queue, user_id)
    await update.message.reply_text("✅ Кабинет WB подключён.\n\nТеперь можно обновить данные:\n/update")


async def disconnect_command(update, context):
    bot = get_bot()
    if not await bot.access(update, "disconnect"):
        return
    user_id = bot.uid(update)
    disconnect_wb_account(user_id)
    log_privileged_action(user_id, "/disconnect", get_user_role(user_id), "disconnect_token", "success")
    await update.message.reply_text("✅ Подключение кабинета удалено. WB-токен очищен из профиля.")
