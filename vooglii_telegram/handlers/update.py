from __future__ import annotations

from vooglii_telegram.services.account_service import is_wb_connected
from vooglii_telegram.services.sync_service import format_sync_result, run_user_sync

from ._bot import get_bot


async def update_command(update, context):
    bot = get_bot()
    if not await bot.access(update, "update"):
        return
    user_id = bot.uid(update)
    token = bot.get_user_token(user_id)
    if not is_wb_connected(user_id) or not token:
        await update.message.reply_text(bot.update_no_cabinet_text())
        return
    await update.message.reply_text(bot.update_started_text())
    result = run_user_sync(user_id, token, 30)
    await update.message.reply_text(format_sync_result(result))
