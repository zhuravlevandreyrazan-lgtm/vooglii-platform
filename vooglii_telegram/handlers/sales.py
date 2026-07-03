from __future__ import annotations

from ._bot import get_bot


async def sales_command(update, context):
    bot = get_bot()
    return await bot._sales_command_entry(update, context)


async def orders_command(update, context):
    bot = get_bot()
    return await bot._orders_command_entry(update, context)
