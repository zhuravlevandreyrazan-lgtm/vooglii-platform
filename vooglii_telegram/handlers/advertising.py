from __future__ import annotations

from ._bot import get_bot


async def advert_command(update, context):
    bot = get_bot()
    return await bot._advert_command_entry(update, context)


async def ads_command(update, context):
    bot = get_bot()
    return await bot._ads_command_entry(update, context)


async def adsupdate_command(update, context):
    bot = get_bot()
    return await bot._adsupdate_command_entry(update, context)


async def adsaudit_command(update, context):
    bot = get_bot()
    return await bot._adsaudit_command_entry(update, context)
