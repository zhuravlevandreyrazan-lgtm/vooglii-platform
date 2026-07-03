from __future__ import annotations

from ._bot import get_bot


async def products_command(update, context):
    bot = get_bot()
    return await bot._products_command_entry(update, context)
