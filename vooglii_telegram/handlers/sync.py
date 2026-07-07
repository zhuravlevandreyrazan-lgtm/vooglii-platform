from __future__ import annotations

from vooglii_telegram.services.sync_service import build_sync_history_text, build_sync_status_text

from ._bot import get_bot


async def sync_command(update, context):
    bot = get_bot()
    if not await bot.access(update, "update"):
        return
    mode = str((context.args or ["status"])[0]).strip().lower() if getattr(context, "args", None) else "status"
    user_id = bot.uid(update)
    if mode == "history":
        await update.message.reply_text(build_sync_history_text(user_id))
        return
    await update.message.reply_text(build_sync_status_text(user_id))
