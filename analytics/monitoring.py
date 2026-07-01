from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

from analytics.build_info import get_build_info
from analytics.common import now_iso
from analytics.env import get_environment_snapshot

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


APP_STARTED_AT = time.monotonic()


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_uptime_seconds() -> float:
    return round(time.monotonic() - APP_STARTED_AT, 2)


def get_memory_usage_mb() -> float | None:
    if psutil is None:
        return None
    try:
        process = psutil.Process(os.getpid())
        return round(float(process.memory_info().rss) / (1024 * 1024), 2)
    except Exception:
        return None


def get_health_snapshot(runtime_mode: str = "live", backend_status: str = "ok") -> dict[str, Any]:
    build_info = get_build_info()
    env_snapshot = get_environment_snapshot()
    return {
        "status": backend_status,
        "uptimeSeconds": get_uptime_seconds(),
        "memoryUsageMb": get_memory_usage_mb(),
        "pythonVersion": sys.version.split()[0],
        "platform": platform.platform(),
        "applicationVersion": build_info["version"],
        "frontendVersion": build_info["frontendVersion"],
        "environment": env_snapshot["environment"],
        "runtimeMode": runtime_mode,
        "buildInfo": build_info,
        "timestamp": now_iso(),
    }


def get_metrics_snapshot(performance: dict[str, Any] | None = None, startup: dict[str, Any] | None = None) -> dict[str, Any]:
    build_info = get_build_info()
    performance = performance or {}
    startup = startup or {}
    return {
        "build": build_info,
        "uptimeSeconds": get_uptime_seconds(),
        "memoryUsageMb": get_memory_usage_mb(),
        "pythonVersion": sys.version.split()[0],
        "workingDirectory": str(_repo_root()),
        "startupValidation": startup,
        "performance": performance,
        "timestamp": now_iso(),
    }
