from __future__ import annotations

from ._bot import get_bot


async def start_command(update, context):
    bot = get_bot()
    return await bot._start_command_entry(update, context)
