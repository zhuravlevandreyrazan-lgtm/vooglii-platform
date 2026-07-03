from __future__ import annotations

from . import get_bot


def admin(update_like):
    bot = get_bot()
    return bot.permission_is_admin(bot.uid(update_like))


def developer(update_like):
    bot = get_bot()
    return bot.has_permission(bot.uid(update_like), "command.developer")


async def access(update, feature=None):
    bot = get_bot()
    user_id = bot.uid(update)
    permission = bot.permission_for_feature(feature)
    permission_result = bot.require_permission(user_id, permission)
    if not permission_result.allowed:
        bot.log_privileged_action(
            user_id,
            f'/{feature or "unknown"}',
            permission_result.role,
            "permission_denied",
            "denied",
            {"permission": permission_result.permission},
        )
        await update.message.reply_text(
            "🔒 У вас нет доступа к этой команде. Если нужен расширенный доступ, обратитесь к владельцу кабинета."
        )
        return False
    if not bot.user_has_access(user_id, feature):
        await update.message.reply_text(bot._pro_upsell_text())
        return False
    return True


async def enforce_command_permission(update, command_name):
    bot = get_bot()
    permission = bot.permission_for_command(command_name)
    if not permission:
        return True
    user_id = bot.uid(update)
    result = bot.require_permission(user_id, permission)
    if result.allowed:
        return True
    bot.log_privileged_action(
        user_id,
        f"/{command_name}",
        result.role,
        "command_denied",
        "denied",
        {"permission": permission},
    )
    await update.message.reply_text("🔒 Команда недоступна для вашей роли.")
    return False


def wrap_command_handler(command_name, handler):
    async def _wrapped(update, context):
        if not await enforce_command_permission(update, command_name):
            return
        await handler(update, context)

    return _wrapped
