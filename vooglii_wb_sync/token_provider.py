from __future__ import annotations

from dataclasses import dataclass

from vooglii_telegram.services.token_resolver import resolve_wb_token


@dataclass
class SyncToken:
    token: str | None
    source: str
    status: str
    reason: str | None = None


def resolve_sync_token(user_id: int, token: str | None = None) -> SyncToken:
    value = str(token or "").strip()
    if value:
        return SyncToken(token=value, source="function_arg", status="OK")
    resolution = resolve_wb_token(int(user_id))
    return SyncToken(
        token=resolution.token,
        source=resolution.source,
        status="OK" if resolution.token else "NO_TOKEN",
        reason=resolution.reason,
    )
