from __future__ import annotations

from datetime import datetime

import load_sales


SYNC_OK = "OK"
SYNC_PARTIAL = "PARTIAL"
SYNC_API_LIMIT = "API_LIMIT"
SYNC_NO_TOKEN = "NO_TOKEN"
SYNC_UNAVAILABLE = "UNAVAILABLE"
SYNC_ERROR = "ERROR"


def parse_status_kind(status: str | None) -> str:
    value = str(status or "").upper()
    if value in ("SUCCESS", "OK"):
        return SYNC_OK
    if value in ("NO_TOKEN", "NO_WB_TOKEN"):
        return SYNC_NO_TOKEN
    if value.startswith(("RATE_LIMIT", "SKIPPED_COOLDOWN", "ADS_COOLDOWN", "FULLSTATS_429", "ADS_STEP_COOLDOWN")):
        return SYNC_API_LIMIT
    if value.startswith(("WB_API_UNAVAILABLE_FOR_PERIOD", "UNAVAILABLE")):
        return SYNC_UNAVAILABLE
    if "PARTIAL" in value:
        return SYNC_PARTIAL
    if value == "MISSING_COST_VALUES":
        return SYNC_PARTIAL
    if value.startswith("EMPTY"):
        return SYNC_PARTIAL
    return SYNC_ERROR


def next_allowed_at(user_id: int, block: str) -> str | None:
    row = load_sales.get_api_cooldown(int(user_id), str(block)) or {}
    return row.get("retry_after")


def next_allowed_seconds(user_id: int, block: str) -> int | None:
    next_at = next_allowed_at(user_id, block)
    if not next_at:
        return None
    retry_dt = load_sales._parse_dt(next_at)
    if retry_dt is None:
        return None
    seconds = int((retry_dt - datetime.now()).total_seconds())
    return max(0, seconds)
