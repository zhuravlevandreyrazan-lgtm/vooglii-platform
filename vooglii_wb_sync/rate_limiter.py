from __future__ import annotations

from datetime import datetime, timedelta

import load_sales


SYNC_OK = "OK"
SYNC_PARTIAL = "PARTIAL"
SYNC_API_LIMIT = "API_LIMIT"
SYNC_NO_TOKEN = "NO_TOKEN"
SYNC_UNAVAILABLE = "UNAVAILABLE"
SYNC_ERROR = "ERROR"

DEFAULT_RETRY_SECONDS = {
    "sales": 10 * 60,
    "orders": 10 * 60,
    "finance": 30 * 60,
    "advertising": 60 * 60,
    "stocks": 10 * 60,
}


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


def _normalize_block(block: str) -> str:
    value = str(block or "").strip().lower()
    if value == "products":
        return "sales"
    return value


def _retry_seconds_from_status(status: str | None) -> int | None:
    value = str(status or "").strip()
    for prefix in ("RATE_LIMIT:", "FULLSTATS_429:", "FULLSTATS_429_SAFE_COOLDOWN:", "ADS_COOLDOWN:", "ADS_STEP_COOLDOWN:"):
        if value.startswith(prefix):
            try:
                seconds_text = value.split(":", 1)[1].strip().split()[0]
                return max(0, int(float(seconds_text)))
            except Exception:
                return None
    return None


def resolve_retry_policy(
    user_id: int,
    block: str,
    status: str | None,
    *,
    next_allowed: str | None = None,
    now: str | None = None,
) -> dict[str, object]:
    block_name = _normalize_block(block)
    if next_allowed:
        retry_dt = load_sales._parse_dt(str(next_allowed))
        if retry_dt is not None:
            return {
                "retry_at": retry_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "retry_source": "cooldown",
                "retry_seconds": max(0, int((retry_dt - datetime.now()).total_seconds())),
                "retry_is_approximate": False,
            }

    cooldown_retry_at = next_allowed_at(int(user_id), block_name)
    if cooldown_retry_at:
        retry_dt = load_sales._parse_dt(str(cooldown_retry_at))
        if retry_dt is not None:
            return {
                "retry_at": retry_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "retry_source": "cooldown",
                "retry_seconds": max(0, int((retry_dt - datetime.now()).total_seconds())),
                "retry_is_approximate": False,
            }

    header_seconds = _retry_seconds_from_status(status)
    base_now = load_sales._parse_dt(str(now)) if now else None
    if base_now is None:
        base_now = load_sales._parse_dt(load_sales._now_str()) or datetime.now()
    if header_seconds is not None:
        retry_dt = base_now + timedelta(seconds=int(header_seconds))
        return {
            "retry_at": retry_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "retry_source": "api_header",
            "retry_seconds": int(header_seconds),
            "retry_is_approximate": False,
        }

    default_seconds = int(DEFAULT_RETRY_SECONDS.get(block_name, 10 * 60))
    retry_dt = base_now + timedelta(seconds=default_seconds)
    return {
        "retry_at": retry_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "retry_source": "default_policy",
        "retry_seconds": default_seconds,
        "retry_is_approximate": True,
    }
