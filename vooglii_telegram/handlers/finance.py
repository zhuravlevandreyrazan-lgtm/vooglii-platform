from __future__ import annotations

from ._bot import get_bot


async def finance_command(update, context):
    bot = get_bot()
    return await bot._finance_command_entry(update, context)
