from __future__ import annotations

from ._bot import get_bot


async def system_command(update, context):
    bot = get_bot()
    return await bot._system_command_entry(update, context)
