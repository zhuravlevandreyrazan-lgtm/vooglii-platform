from __future__ import annotations

from ._bot import get_bot


async def control_command(update, context):
    bot = get_bot()
    return await bot._control_command_entry(update, context)


async def migration_command(update, context):
    bot = get_bot()
    return await bot._migration_command_entry(update, context)


async def performance_command(update, context):
    bot = get_bot()
    return await bot._performance_command_entry(update, context)


async def structure_command(update, context):
    bot = get_bot()
    return await bot._structure_command_entry(update, context)


async def telegram_command(update, context):
    bot = get_bot()
    return await bot._telegram_command_entry(update, context)


async def ui_command(update, context):
    bot = get_bot()
    return await bot._ui_command_entry(update, context)


async def rc_command(update, context):
    bot = get_bot()
    return await bot._rc_command_entry(update, context)


async def data_command(update, context):
    bot = get_bot()
    return await bot._data_command_entry(update, context)
