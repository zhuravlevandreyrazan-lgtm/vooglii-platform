from __future__ import annotations

import threading
import time
from typing import Any


_LOCK = threading.Lock()
_ENDPOINT_STATS: dict[str, dict[str, Any]] = {}


def now_monotonic_ms() -> float:
    return time.perf_counter() * 1000.0


def record_endpoint_result(
    endpoint: str,
    *,
    duration_ms: float,
    success: bool,
    source: str,
    cached: bool,
    stale: bool,
    degraded: bool,
    error: str | None = None,
) -> None:
    with _LOCK:
        stats = _ENDPOINT_STATS.setdefault(
            endpoint,
            {
                "calls": 0,
                "errors": 0,
                "last_duration_ms": None,
                "last_success_at": None,
                "last_error": None,
                "last_error_at": None,
                "last_source": None,
                "last_cached": False,
                "last_stale": False,
                "last_degraded": False,
                "cached_calls": 0,
                "degraded_calls": 0,
                "stale_calls": 0,
                "max_duration_ms": 0.0,
            },
        )
        stats["calls"] += 1
        stats["last_duration_ms"] = round(float(duration_ms), 2)
        stats["last_source"] = source
        stats["last_cached"] = bool(cached)
        stats["last_stale"] = bool(stale)
        stats["last_degraded"] = bool(degraded)
        stats["max_duration_ms"] = round(max(float(stats["max_duration_ms"] or 0.0), float(duration_ms)), 2)
        if cached:
            stats["cached_calls"] += 1
        if degraded:
            stats["degraded_calls"] += 1
        if stale:
            stats["stale_calls"] += 1
        if success:
            stats["last_success_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        else:
            stats["errors"] += 1
            stats["last_error"] = error
            stats["last_error_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def build_runtime_metadata(
    *,
    duration_ms: float,
    cached: bool,
    stale: bool,
    degraded: bool,
    source: str,
) -> dict[str, Any]:
    return {
        "duration_ms": round(float(duration_ms), 2),
        "cached": bool(cached),
        "stale": bool(stale),
        "degraded": bool(degraded),
        "source": source,
    }


def get_performance_snapshot() -> dict[str, Any]:
    with _LOCK:
        return {key: dict(value) for key, value in _ENDPOINT_STATS.items()}


def get_slow_endpoints(budgets_ms: dict[str, int]) -> list[dict[str, Any]]:
    slow = []
    with _LOCK:
        for endpoint, stats in _ENDPOINT_STATS.items():
            budget = budgets_ms.get(endpoint)
            duration = float(stats.get("last_duration_ms") or 0.0)
            if budget is not None and duration > budget:
                slow.append(
                    {
                        "endpoint": endpoint,
                        "duration_ms": duration,
                        "budget_ms": budget,
                        "source": stats.get("last_source"),
                    }
                )
    return sorted(slow, key=lambda item: float(item.get("duration_ms") or 0), reverse=True)
