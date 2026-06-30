from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import telegram_bot

PRODUCT_NAME = "VOOGLII"
API_VERSION = "v1"
DEFAULT_USER_ID = int((getattr(telegram_bot, "ADMIN_IDS", None) or [658486226])[0])


def _read_build_version() -> str:
    version_path = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        version = version_path.read_text(encoding="utf-8").strip()
        return version or "0.9.0-rc1"
    except Exception:
        return "0.9.0-rc1"


BUILD_VERSION = _read_build_version()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_month_days() -> tuple[str, str]:
    period_snapshot = telegram_bot._period_engine_snapshot(args=["current_month"])
    start_date = str(period_snapshot.get("start_date") or datetime.now().strftime("%Y-%m-01"))
    end_date = str(period_snapshot.get("end_date") or datetime.now().strftime("%Y-%m-%d"))
    return start_date, end_date


def snapshot_context():
    return telegram_bot._snapshot_context() if hasattr(telegram_bot, "_snapshot_context") else None


def safe_text(value: Any, default: str = "UNKNOWN") -> str:
    text = str(value or "").strip()
    return text if text else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return round(float(value), 2)
    except Exception:
        return default


def safe_list(items: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in list(items or []):
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def status_to_api(value: Any) -> str:
    normalized = safe_text(value).upper()
    if normalized in ("GOOD", "READY", "OK", "HEALTHY", "NORMAL", "MATCHED", "AVAILABLE"):
        return "GOOD"
    if normalized in ("WARNING", "PARTIAL", "ALMOST_READY", "MIGRATED_PARTIAL", "DEGRADED", "DETAIL_REQUIRED"):
        return "WARNING"
    if normalized in ("CRITICAL", "BLOCKED", "ERROR", "FORBIDDEN", "UNAVAILABLE", "UNAUTHORIZED", "RATE_LIMIT", "INSUFFICIENT_DATA"):
        return "CRITICAL"
    return "UNKNOWN"


def status_to_tone(value: Any) -> str:
    normalized = status_to_api(value)
    if normalized == "GOOD":
        return "healthy"
    if normalized == "WARNING":
        return "watch"
    if normalized == "CRITICAL":
        return "risk"
    return "neutral"


def status_to_severity(value: Any) -> str:
    normalized = status_to_api(value)
    if normalized == "CRITICAL":
        return "high"
    if normalized == "WARNING":
        return "medium"
    if normalized == "GOOD":
        return "low"
    return "info"


def format_confidence(value: Any) -> str:
    normalized = safe_text(value).upper()
    if normalized in ("HIGH", "MEDIUM", "LOW"):
        return normalized.title()
    score = safe_int(value, 50)
    if score >= 85:
        return "High"
    if score >= 65:
        return "Medium"
    return "Low"


def route_for_workspace(name: str) -> str:
    mapping = {
        "executive": "/executive",
        "business": "/business",
        "finance": "/finance",
        "advertising": "/advertising",
        "products": "/products",
        "inventory": "/inventory",
        "advisor": "/advisor",
        "reports": "/reports",
        "system": "/system",
    }
    return mapping.get(str(name or "").lower(), "/")


def safe_call(name: str, builder) -> tuple[dict[str, Any], str | None]:
    try:
        result = builder()
        if isinstance(result, dict):
            return result, None
        return {}, f"{name} returned non-dict payload"
    except Exception as exc:
        return {}, f"{name} unavailable: {exc}"


def git_revision() -> str:
    head_path = Path(".git/HEAD")
    if not head_path.exists():
        return "unknown"
    try:
        head_value = head_path.read_text(encoding="utf-8").strip()
        if head_value.startswith("ref:"):
            ref_path = Path(".git") / head_value.split(" ", 1)[1].strip()
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()[:12]
        return head_value[:12]
    except Exception:
        return "unknown"
