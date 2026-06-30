from __future__ import annotations

import threading
from queue import Queue
from typing import Any, Callable

from analytics.cache import get_cache_value, get_stale_cache_value, set_cache_value
from analytics.performance import build_runtime_metadata, now_monotonic_ms, record_endpoint_result


class SnapshotTimeoutError(RuntimeError):
    pass


def run_with_timeout(builder: Callable[[], dict[str, Any]], timeout_ms: int) -> dict[str, Any]:
    queue: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def _runner() -> None:
        try:
            queue.put(("result", builder()))
        except Exception as exc:
            queue.put(("error", exc))

    thread = threading.Thread(target=_runner, name="vooglii-api-timeout", daemon=True)
    thread.start()
    thread.join(max(float(timeout_ms), 1.0) / 1000.0)
    if thread.is_alive():
        raise SnapshotTimeoutError(f"Snapshot build timed out after {timeout_ms} ms")

    if queue.empty():
        return {}

    kind, value = queue.get()
    if kind == "error":
        raise value
    return dict(value or {})


def with_runtime(payload: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["runtime"] = runtime
    return result


def safe_build_snapshot(
    *,
    endpoint: str,
    cache_key: str,
    ttl_seconds: int,
    timeout_ms: int,
    builder: Callable[[], dict[str, Any]],
    degraded_builder: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    started_at = now_monotonic_ms()

    cached_value = get_cache_value(cache_key)
    if cached_value is not None:
        duration_ms = now_monotonic_ms() - started_at
        runtime = build_runtime_metadata(
            duration_ms=duration_ms,
            cached=True,
            stale=False,
            degraded=bool((cached_value.get("runtime") or {}).get("degraded")),
            source="cache",
        )
        payload = with_runtime(cached_value, runtime)
        record_endpoint_result(
            endpoint,
            duration_ms=duration_ms,
            success=True,
            source="cache",
            cached=True,
            stale=False,
            degraded=runtime["degraded"],
        )
        return payload

    try:
        live_payload = run_with_timeout(builder, timeout_ms)
        duration_ms = now_monotonic_ms() - started_at
        runtime = build_runtime_metadata(
            duration_ms=duration_ms,
            cached=False,
            stale=False,
            degraded=False,
            source="live",
        )
        payload = with_runtime(live_payload, runtime)
        set_cache_value(cache_key, payload, ttl_seconds)
        record_endpoint_result(
            endpoint,
            duration_ms=duration_ms,
            success=True,
            source="live",
            cached=False,
            stale=False,
            degraded=False,
        )
        return payload
    except Exception as exc:
        stale_value = get_stale_cache_value(cache_key)
        duration_ms = now_monotonic_ms() - started_at
        if stale_value is not None:
            runtime = build_runtime_metadata(
                duration_ms=duration_ms,
                cached=True,
                stale=True,
                degraded=True,
                source="stale_cache",
            )
            payload = with_runtime(stale_value, runtime)
            record_endpoint_result(
                endpoint,
                duration_ms=duration_ms,
                success=False,
                source="stale_cache",
                cached=True,
                stale=True,
                degraded=True,
                error=str(exc),
            )
            return payload

        degraded_payload = degraded_builder(str(exc))
        runtime = build_runtime_metadata(
            duration_ms=duration_ms,
            cached=False,
            stale=False,
            degraded=True,
            source="degraded",
        )
        payload = with_runtime(degraded_payload, runtime)
        record_endpoint_result(
            endpoint,
            duration_ms=duration_ms,
            success=False,
            source="degraded",
            cached=False,
            stale=False,
            degraded=True,
            error=str(exc),
        )
        return payload
