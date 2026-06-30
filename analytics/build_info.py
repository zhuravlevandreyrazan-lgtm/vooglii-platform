from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from analytics.common import API_VERSION, BUILD_VERSION, git_revision, now_iso


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _frontend_package_version() -> str:
    package_path = _repo_root() / "frontend" / "package.json"
    try:
        payload = json.loads(package_path.read_text(encoding="utf-8"))
        version = str(payload.get("version") or "").strip()
        return version or "unknown"
    except Exception:
        return "unknown"


def get_build_environment() -> str:
    return str(os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()


def get_build_type() -> str:
    if "rc" in BUILD_VERSION.lower():
        return "release_candidate"
    return "production" if get_build_environment() == "production" else "development"


def get_build_timestamp() -> str:
    return str(os.getenv("BUILD_TIMESTAMP") or now_iso())


def get_build_info() -> dict[str, Any]:
    return {
        "version": BUILD_VERSION,
        "buildTimestamp": get_build_timestamp(),
        "git": git_revision(),
        "environment": get_build_environment(),
        "apiVersion": API_VERSION,
        "buildType": get_build_type(),
        "frontendVersion": _frontend_package_version(),
    }
