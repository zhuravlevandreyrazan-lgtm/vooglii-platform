from __future__ import annotations

from ._bot import get_bot


async def profile_command(update, context):
    bot = get_bot()
    return await bot._profile_command_entry(update, context)


async def account_command(update, context):
    bot = get_bot()
    return await bot._account_command_entry(update, context)
