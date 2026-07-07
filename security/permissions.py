from __future__ import annotations

from dataclasses import dataclass

from config import ADMIN_IDS
from db_manager import get_conn, init_db


ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_VIEWER = "viewer"
ROLE_SUPPORT = "support"
ROLE_DEVELOPER = "developer"
LEGACY_ROLE_ACCOUNTANT = "accountant"

ALL_ROLES = {
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_VIEWER,
    ROLE_SUPPORT,
    ROLE_DEVELOPER,
    LEGACY_ROLE_ACCOUNTANT,
}

CUSTOMER_PERMISSION_MAP = {
    "start": "customer.start",
    "help": "customer.help",
    "menu": "customer.menu",
    "connect": "customer.connect",
    "disconnect": "customer.disconnect",
    "update": "customer.update",
    "report": "customer.report",
    "today": "customer.report",
    "week": "customer.report",
    "month": "customer.report",
    "product": "customer.products",
    "products": "customer.products",
    "stocks": "customer.stocks",
    "orders": "customer.orders",
    "funnel": "customer.orders",
    "status": "customer.status",
    "profile": "customer.profile",
    "tariff": "customer.tariff",
    "buy": "customer.tariff",
    "pro": "customer.tariff",
    "business": "customer.business",
    "finance": "customer.finance",
    "advert": "customer.advert",
    "analytics": "customer.analytics",
    "system": "customer.system",
    "advisor": "customer.advisor",
    "dashboard": "customer.dashboard",
    "home": "customer.dashboard",
    "forecast": "customer.forecast",
    "validate": "customer.report",
}

_READONLY_CUSTOMER_PERMISSIONS = {
    "customer.start",
    "customer.help",
    "customer.menu",
    "customer.report",
    "customer.products",
    "customer.stocks",
    "customer.orders",
    "customer.status",
    "customer.profile",
    "customer.tariff",
    "customer.business",
    "customer.finance",
    "customer.advert",
    "customer.analytics",
    "customer.system",
    "customer.advisor",
    "customer.dashboard",
    "customer.forecast",
}

ROLE_PERMISSIONS = {
    ROLE_OWNER: {"*"},
    ROLE_ADMIN: {"*"},
    ROLE_DEVELOPER: {"*"},
    ROLE_SUPPORT: {
        "command.admin",
        "command.support",
        "command.system",
        "help.developer",
        "customer.help",
        "customer.menu",
        "customer.status",
        "customer.system",
        "customer.profile",
    },
    ROLE_MANAGER: _READONLY_CUSTOMER_PERMISSIONS | {"customer.connect", "customer.disconnect", "customer.update"},
    LEGACY_ROLE_ACCOUNTANT: _READONLY_CUSTOMER_PERMISSIONS,
    ROLE_VIEWER: _READONLY_CUSTOMER_PERMISSIONS,
}

PRIVILEGED_COMMANDS = {
    "admin": "command.admin",
    "telegram": "command.developer",
    "ui": "command.developer",
    "performance": "command.system",
    "migration": "command.system",
    "control": "command.admin",
    "structure": "command.system",
    "health": "command.system",
    "apistatus": "command.admin",
    "adsfullstatsprobe": "command.developer",
    "syncstatus": "command.admin",
    "rc": "command.developer",
    "data": "command.developer",
}


@dataclass(frozen=True)
class PermissionCheckResult:
    allowed: bool
    role: str
    permission: str


def normalize_role(role: str | None) -> str:
    text = str(role or "").strip().lower()
    if text == LEGACY_ROLE_ACCOUNTANT:
        return ROLE_MANAGER
    return text if text in ALL_ROLES else ROLE_VIEWER


def _fetch_user_security_row(user_id: int) -> tuple[str, int] | None:
    init_db()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT role, is_active FROM users WHERE telegram_id=?",
            (int(user_id or 0),),
        ).fetchone()
        return (str(row[0] or ""), int(row[1] or 0)) if row else None
    finally:
        conn.close()


def get_user_role(user_id: int) -> str:
    if int(user_id or 0) in ADMIN_IDS:
        row = _fetch_user_security_row(user_id)
        role = normalize_role(row[0] if row else ROLE_OWNER)
        return role if role != ROLE_VIEWER else ROLE_ADMIN
    row = _fetch_user_security_row(user_id)
    return normalize_role(row[0] if row else ROLE_VIEWER)


def is_active_user(user_id: int) -> bool:
    row = _fetch_user_security_row(user_id)
    return bool(row and int(row[1] or 0) == 1)


def _bootstrap_allowed(permission: str) -> bool:
    return permission in {
        "customer.start",
        "customer.help",
        "customer.menu",
        "customer.connect",
    }


def _permission_set_for_role(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS[ROLE_VIEWER]))


def has_permission(user_id: int, permission: str) -> bool:
    if not permission:
        return is_active_user(user_id)
    if _fetch_user_security_row(user_id) is None and _bootstrap_allowed(permission):
        return True
    role = get_user_role(user_id)
    permissions = _permission_set_for_role(role)
    return is_active_user(user_id) and ("*" in permissions or permission in permissions)


def require_permission(user_id: int, permission: str) -> PermissionCheckResult:
    role = get_user_role(user_id)
    return PermissionCheckResult(
        allowed=has_permission(user_id, permission),
        role=role,
        permission=permission,
    )


def is_admin(user_id: int) -> bool:
    if int(user_id or 0) in ADMIN_IDS:
        return True
    return has_permission(user_id, "command.admin")


def is_developer(user_id: int) -> bool:
    return has_permission(user_id, "command.developer")


def permission_for_feature(feature: str | None) -> str:
    text = str(feature or "").strip().lower()
    return CUSTOMER_PERMISSION_MAP.get(text, f"customer.{text}" if text else "")


def permission_for_command(command_name: str | None) -> str:
    text = str(command_name or "").strip().lower()
    if text in PRIVILEGED_COMMANDS:
        return PRIVILEGED_COMMANDS[text]
    return permission_for_feature(text)
