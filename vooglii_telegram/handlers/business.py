from __future__ import annotations

from ._bot import get_bot


async def business_command(update, context):
    bot = get_bot()
    return await bot._business_command_entry(update, context)
