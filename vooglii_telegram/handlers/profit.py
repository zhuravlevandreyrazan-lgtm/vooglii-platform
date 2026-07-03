from __future__ import annotations

from ._bot import get_bot


async def profit_command(update, context):
    bot = get_bot()
    return await bot._profit_command_entry(update, context)


async def cashflow_command(update, context):
    bot = get_bot()
    return await bot._cashflow_command_entry(update, context)


async def expense_command(update, context):
    bot = get_bot()
    return await bot._expense_command_entry(update, context)


async def topprofit_command(update, context):
    bot = get_bot()
    return await bot._topprofit_command_entry(update, context)


async def losers_command(update, context):
    bot = get_bot()
    return await bot._losers_command_entry(update, context)


async def categories_command(update, context):
    bot = get_bot()
    return await bot._categories_command_entry(update, context)


async def abc_command(update, context):
    bot = get_bot()
    return await bot._abc_command_entry(update, context)
