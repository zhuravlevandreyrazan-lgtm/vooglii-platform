from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request


ROLE_ORDER = ["viewer", "analyst", "manager", "admin", "owner"]
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "dashboard:view",
        "reports:view",
    },
    "analyst": {
        "dashboard:view",
        "reports:view",
        "analytics:view",
        "ads:view",
        "finance:view",
    },
    "manager": {
        "dashboard:view",
        "reports:view",
        "analytics:view",
        "ads:view",
        "finance:view",
        "users:view",
    },
    "admin": {
        "dashboard:view",
        "reports:view",
        "analytics:view",
        "ads:view",
        "finance:view",
        "users:view",
        "users:manage",
        "settings:manage",
    },
    "owner": {
        "dashboard:view",
        "reports:view",
        "analytics:view",
        "ads:view",
        "finance:view",
        "users:view",
        "users:manage",
        "settings:manage",
    },
}

DEFAULT_ACTOR_ID = "user_owner_001"
ACTOR_HEADER = "x-vooglii-actor-id"

_DIRECTORY: list[dict[str, Any]] = [
    {
        "id": "user_owner_001",
        "name": "Andrey Voronov",
        "email": "founder@vooglii.local",
        "role": "owner",
        "enabled": True,
        "avatarUrl": None,
        "createdAt": "2026-06-01T09:00:00Z",
        "lastActiveAt": "2026-07-01T00:00:00Z",
        "deactivatedAt": None,
    },
    {
        "id": "user_admin_001",
        "name": "Daria Kuznetsova",
        "email": "ops-admin@vooglii.local",
        "role": "admin",
        "enabled": True,
        "avatarUrl": None,
        "createdAt": "2026-06-04T10:00:00Z",
        "lastActiveAt": "2026-06-30T16:20:00Z",
        "deactivatedAt": None,
    },
    {
        "id": "user_manager_001",
        "name": "Maksim Petrov",
        "email": "manager@vooglii.local",
        "role": "manager",
        "enabled": True,
        "avatarUrl": None,
        "createdAt": "2026-06-07T11:20:00Z",
        "lastActiveAt": "2026-06-30T14:10:00Z",
        "deactivatedAt": None,
    },
    {
        "id": "user_analyst_001",
        "name": "Elena Smirnova",
        "email": "analyst@vooglii.local",
        "role": "analyst",
        "enabled": True,
        "avatarUrl": None,
        "createdAt": "2026-06-08T12:30:00Z",
        "lastActiveAt": "2026-06-30T12:45:00Z",
        "deactivatedAt": None,
    },
    {
        "id": "user_viewer_001",
        "name": "Ivan Sokolov",
        "email": "viewer@vooglii.local",
        "role": "viewer",
        "enabled": True,
        "avatarUrl": None,
        "createdAt": "2026-06-10T15:00:00Z",
        "lastActiveAt": "2026-06-29T18:00:00Z",
        "deactivatedAt": None,
    },
]
_AUDIT_LOG: list[dict[str, Any]] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_roles() -> list[str]:
    return list(ROLE_ORDER)


def get_role_permissions(role: str) -> list[str]:
    permissions = ROLE_PERMISSIONS.get(role, set())
    return sorted(permissions)


def build_user_profile(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "name": str(record["name"]),
        "email": str(record["email"]),
        "role": str(record["role"]),
        "permissions": get_role_permissions(str(record["role"])),
        "enabled": bool(record.get("enabled", True)),
        "avatarUrl": record.get("avatarUrl"),
        "createdAt": str(record["createdAt"]),
        "lastActiveAt": record.get("lastActiveAt"),
        "deactivatedAt": record.get("deactivatedAt"),
    }


def _find_user(user_id: str) -> dict[str, Any]:
    for item in _DIRECTORY:
        if str(item.get("id")) == user_id:
            return item
    raise KeyError(user_id)


def get_actor_by_id(user_id: str | None) -> dict[str, Any]:
    try:
        record = _find_user(str(user_id or DEFAULT_ACTOR_ID))
    except KeyError as exc:
        raise HTTPException(status_code=401, detail="Unknown actor.") from exc
    return build_user_profile(record)


def log_audit_event(
    *,
    event: str,
    actor_id: str,
    target_id: str | None = None,
    outcome: str = "ok",
    detail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "id": f"audit_{len(_AUDIT_LOG) + 1:04d}",
        "event": event,
        "actorId": actor_id,
        "targetId": target_id,
        "outcome": outcome,
        "detail": detail,
        "metadata": metadata or {},
        "createdAt": _now_iso(),
    }
    _AUDIT_LOG.insert(0, entry)
    return entry


def list_users() -> list[dict[str, Any]]:
    return [build_user_profile(item) for item in _DIRECTORY]


def list_audit_events() -> list[dict[str, Any]]:
    return deepcopy(_AUDIT_LOG)


def resolve_actor(request: Request) -> dict[str, Any]:
    actor_id = request.headers.get(ACTOR_HEADER) or DEFAULT_ACTOR_ID
    actor = get_actor_by_id(actor_id)
    if not actor["enabled"]:
        log_audit_event(
            event="rbac.access_denied",
            actor_id=str(actor["id"]),
            outcome="denied",
            detail="Disabled actor attempted to access the API.",
            metadata={"path": request.url.path},
        )
        raise HTTPException(status_code=403, detail="User account is disabled.")
    return actor


def actor_has_permission(actor: dict[str, Any], permission: str) -> bool:
    return permission in set(actor.get("permissions") or [])


def require_permission(permission: str):
    def dependency(request: Request) -> dict[str, Any]:
        actor = resolve_actor(request)
        if not actor_has_permission(actor, permission):
            log_audit_event(
                event="rbac.access_denied",
                actor_id=str(actor["id"]),
                outcome="denied",
                detail=f"Missing permission: {permission}",
                metadata={"path": request.url.path, "permission": permission},
            )
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return actor

    return dependency


def require_role(*roles: str):
    allowed = set(roles)

    def dependency(request: Request) -> dict[str, Any]:
        actor = resolve_actor(request)
        if str(actor.get("role")) not in allowed:
            log_audit_event(
                event="rbac.access_denied",
                actor_id=str(actor["id"]),
                outcome="denied",
                detail=f"Missing role. Allowed: {', '.join(sorted(allowed))}",
                metadata={"path": request.url.path, "roles": sorted(allowed)},
            )
            raise HTTPException(status_code=403, detail="Missing required role.")
        return actor

    return dependency


def update_user_role(*, actor: dict[str, Any], user_id: str, role: str) -> dict[str, Any]:
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Unsupported role.")
    try:
        record = _find_user(user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc

    enabled_owners = [item for item in _DIRECTORY if item.get("enabled") and item.get("role") == "owner"]
    if record.get("role") == "owner" and role != "owner" and len(enabled_owners) <= 1:
        raise HTTPException(status_code=400, detail="At least one enabled owner must remain.")

    previous_role = str(record["role"])
    record["role"] = role
    record["lastActiveAt"] = _now_iso()
    log_audit_event(
        event="rbac.role_changed",
        actor_id=str(actor["id"]),
        target_id=user_id,
        detail=f"Role changed from {previous_role} to {role}",
        metadata={"from": previous_role, "to": role},
    )
    return build_user_profile(record)


def update_user_enabled(*, actor: dict[str, Any], user_id: str, enabled: bool) -> dict[str, Any]:
    try:
        record = _find_user(user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc

    if str(actor["id"]) == user_id and not enabled:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")

    enabled_owners = [item for item in _DIRECTORY if item.get("enabled") and item.get("role") == "owner"]
    if record.get("role") == "owner" and not enabled and len(enabled_owners) <= 1:
        raise HTTPException(status_code=400, detail="At least one enabled owner must remain.")

    record["enabled"] = enabled
    record["deactivatedAt"] = None if enabled else _now_iso()
    record["lastActiveAt"] = _now_iso()
    log_audit_event(
        event="rbac.user_status_changed",
        actor_id=str(actor["id"]),
        target_id=user_id,
        detail="User enabled" if enabled else "User disabled",
        metadata={"enabled": enabled},
    )
    return build_user_profile(record)
