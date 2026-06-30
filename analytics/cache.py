from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    value: dict[str, Any]
    created_at: float
    expires_at: float


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, CacheEntry] = {}
_CACHE_STATS = {
    "hits": 0,
    "misses": 0,
    "writes": 0,
    "stale_returns": 0,
}


def get_cache_entry(key: str) -> CacheEntry | None:
    with _CACHE_LOCK:
        return _CACHE.get(key)


def get_cache_value(key: str) -> dict[str, Any] | None:
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            _CACHE_STATS["misses"] += 1
            return None
        if entry.expires_at > now:
            _CACHE_STATS["hits"] += 1
            return dict(entry.value)
        _CACHE_STATS["misses"] += 1
        return None


def get_stale_cache_value(key: str) -> dict[str, Any] | None:
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return None
        _CACHE_STATS["stale_returns"] += 1
        return dict(entry.value)


def set_cache_value(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
    now = time.monotonic()
    with _CACHE_LOCK:
        _CACHE[key] = CacheEntry(
            value=dict(value),
            created_at=now,
            expires_at=now + max(int(ttl_seconds), 1),
        )
        _CACHE_STATS["writes"] += 1


def invalidate_cache(key: str) -> None:
    with _CACHE_LOCK:
        _CACHE.pop(key, None)


def list_cache_keys() -> list[str]:
    with _CACHE_LOCK:
        return sorted(_CACHE.keys())


def get_cache_status() -> dict[str, Any]:
    now = time.monotonic()
    with _CACHE_LOCK:
        entries = {
            key: {
                "fresh": entry.expires_at > now,
                "age_seconds": round(max(0.0, now - entry.created_at), 2),
                "ttl_remaining_seconds": round(max(0.0, entry.expires_at - now), 2),
            }
            for key, entry in _CACHE.items()
        }
        return {
            "size": len(_CACHE),
            "keys": sorted(_CACHE.keys()),
            "stats": dict(_CACHE_STATS),
            "entries": entries,
        }
