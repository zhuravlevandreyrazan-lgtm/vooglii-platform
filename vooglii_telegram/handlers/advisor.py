from __future__ import annotations

from ._bot import get_bot


async def advisor_command(update, context):
    bot = get_bot()
    return await bot._advisor_command_entry(update, context)
