from __future__ import annotations

from ._bot import get_bot


async def analytics_command(update, context):
    bot = get_bot()
    return await bot._analytics_command_entry(update, context)
