from __future__ import annotations

from ._bot import get_bot


async def admin_command(update, context):
    bot = get_bot()
    return await bot._admin_command_entry(update, context)


async def health_command(update, context):
    bot = get_bot()
    return await bot._health_command_entry(update, context)


async def syncstatus_command(update, context):
    bot = get_bot()
    return await bot._syncstatus_command_entry(update, context)


async def apistatus_command(update, context):
    bot = get_bot()
    return await bot._apistatus_command_entry(update, context)
