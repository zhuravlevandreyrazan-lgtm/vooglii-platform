from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from analytics.build_info import get_build_info
from analytics.env import validate_required_env


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _validate_version() -> dict[str, Any]:
    version_path = _repo_root() / "VERSION"
    exists = version_path.exists()
    value = version_path.read_text(encoding="utf-8").strip() if exists else ""
    return {
        "exists": exists,
        "value": value or None,
        "valid": bool(value.strip()),
    }


def _validate_directories() -> dict[str, Any]:
    root = _repo_root()
    required = [
        "analytics",
        "frontend",
        "scripts",
    ]
    optional_writable = [
        "exports",
        "backup",
        "restore",
        "storage",
    ]
    return {
        "required": {name: (root / name).exists() for name in required},
        "optionalWritable": {name: ((root / name).exists() or True) for name in optional_writable},
    }


def _validate_writable_paths() -> dict[str, Any]:
    root = _repo_root()
    candidates = [
        root / "exports",
        root / "backup",
        root / "restore",
        root / "storage",
    ]
    results: dict[str, bool] = {}
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            results[str(path.relative_to(root))] = True
        except Exception:
            results[str(path.relative_to(root))] = False
    return results


def validate_startup() -> dict[str, Any]:
    env_validation = validate_required_env()
    version_validation = _validate_version()
    directory_validation = _validate_directories()
    writable_validation = _validate_writable_paths()
    build_info = get_build_info()
    warnings: list[str] = []
    if not version_validation["valid"]:
        warnings.append("VERSION file is missing or empty.")
    if not env_validation["valid"]:
        warnings.append("Required environment variables are missing for the current environment.")

    return {
        "ok": version_validation["valid"] and env_validation["valid"],
        "version": version_validation,
        "environment": env_validation,
        "directories": directory_validation,
        "writable": writable_validation,
        "runtime": {
            "pythonExecutable": os.path.basename(os.sys.executable),
            "build": build_info,
        },
        "warnings": warnings,
    }
