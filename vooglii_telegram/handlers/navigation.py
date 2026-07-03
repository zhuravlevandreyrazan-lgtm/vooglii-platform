from __future__ import annotations

from ._bot import get_bot


async def menu_command(update, context):
    bot = get_bot()
    return await bot._menu_command_entry(update, context)


async def home_command(update, context):
    bot = get_bot()
    return await bot._home_command_entry(update, context)
