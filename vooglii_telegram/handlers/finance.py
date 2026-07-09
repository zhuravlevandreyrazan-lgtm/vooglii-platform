from __future__ import annotations

from vooglii_telegram.ux.financial_modes import automatic_validation_message

from ._bot import get_bot


async def finance_command(update, context):
    bot = get_bot()
    args = list(getattr(context, "args", []) or [])
    if args and str(args[0]).strip().lower() == "validate":
        if not await bot.access(update, "report"):
            return
        if getattr(bot, "_is_engineering_role", None) and bot._is_engineering_role(bot.uid(update)):
            await update.message.reply_text("Engineering validation tools remain available via CLI and admin diagnostics.")
            return
        await update.message.reply_text(automatic_validation_message())
        return

    # Customer /finance should always use the unified finance renderer directly.
    # Legacy subcommands stay routed through the compatibility entrypoint below.
    center_period = bot._customer_command_period(bot.uid(update), args, "current_month")
    if not args or center_period is not None:
        _, days = center_period or bot._customer_command_period(bot.uid(update), ["current_month"], "current_month")
        await bot.send_long(update, bot._finance_center_text(bot.uid(update), days))
        return
    return await bot._finance_command_entry(update, context)
