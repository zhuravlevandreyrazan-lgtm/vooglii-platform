from __future__ import annotations

from vooglii_telegram.ux.financial_modes import finance_validate_summary_text

from ._bot import get_bot


async def finance_command(update, context):
    bot = get_bot()
    args = list(getattr(context, "args", []) or [])
    if args and str(args[0]).strip().lower() == "validate":
        if not await bot.access(update, "report"):
            return
        await update.message.reply_text(finance_validate_summary_text(bot.uid(update)))
        return
    return await bot._finance_command_entry(update, context)
