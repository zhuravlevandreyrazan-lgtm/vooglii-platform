from __future__ import annotations

from ._bot import get_bot


async def stocks_command(update, context):
    bot = get_bot()
    return await bot._stocks_command_entry(update, context)


async def stock_command(update, context):
    bot = get_bot()
    return await bot._stock_command_entry(update, context)


async def forecast_command(update, context):
    bot = get_bot()
    return await bot._forecast_command_entry(update, context)


async def replenishment_command(update, context):
    bot = get_bot()
    return await bot._replenishment_command_entry(update, context)
