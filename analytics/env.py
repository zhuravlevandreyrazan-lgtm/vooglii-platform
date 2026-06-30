from __future__ import annotations

import os
from typing import Any


ENV_DEFAULTS = {
    "APP_ENV": "development",
    "API_HOST": "0.0.0.0",
    "API_PORT": "8000",
    "FRONTEND_PORT": "3000",
    "ALLOWED_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
    "TRUSTED_HOSTS": "localhost,127.0.0.1,testserver",
    "LOG_LEVEL": "INFO",
    "DEMO_MODE_ALLOWED": "true",
    "API_TIMEOUT_MS": "10000",
    "HEALTH_TIMEOUT_MS": "500",
    "REQUIRE_TOKENS": "false",
}

PRODUCTION_REQUIRED_ENV = [
    "APP_ENV",
    "API_HOST",
    "API_PORT",
    "ALLOWED_ORIGINS",
    "TRUSTED_HOSTS",
]


def get_env(name: str, default: str | None = None) -> str:
    if name in os.environ:
        return str(os.environ[name])
    if default is not None:
        return default
    return str(ENV_DEFAULTS.get(name, ""))


def get_allowed_origins() -> list[str]:
    raw = get_env("ALLOWED_ORIGINS", ENV_DEFAULTS["ALLOWED_ORIGINS"])
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_trusted_hosts() -> list[str]:
    raw = get_env("TRUSTED_HOSTS", ENV_DEFAULTS["TRUSTED_HOSTS"])
    hosts = [item.strip() for item in raw.split(",") if item.strip()]
    if "*" in hosts:
        return ["*"]
    environment = get_env("APP_ENV", ENV_DEFAULTS["APP_ENV"]).lower()
    if environment != "production":
        for host in ("localhost", "127.0.0.1", "testserver"):
            if host not in hosts:
                hosts.append(host)
    return hosts


def get_environment_snapshot() -> dict[str, Any]:
    environment = get_env("APP_ENV", ENV_DEFAULTS["APP_ENV"]).lower()
    return {
        "environment": environment,
        "apiHost": get_env("API_HOST", ENV_DEFAULTS["API_HOST"]),
        "apiPort": get_env("API_PORT", ENV_DEFAULTS["API_PORT"]),
        "frontendPort": get_env("FRONTEND_PORT", ENV_DEFAULTS["FRONTEND_PORT"]),
        "allowedOrigins": get_allowed_origins(),
        "trustedHosts": get_trusted_hosts(),
        "logLevel": get_env("LOG_LEVEL", ENV_DEFAULTS["LOG_LEVEL"]),
        "demoModeAllowed": get_env("DEMO_MODE_ALLOWED", ENV_DEFAULTS["DEMO_MODE_ALLOWED"]).lower() == "true",
        "apiTimeoutMs": int(get_env("API_TIMEOUT_MS", ENV_DEFAULTS["API_TIMEOUT_MS"]) or "10000"),
        "healthTimeoutMs": int(get_env("HEALTH_TIMEOUT_MS", ENV_DEFAULTS["HEALTH_TIMEOUT_MS"]) or "500"),
    }


def validate_required_env() -> dict[str, Any]:
    snapshot = get_environment_snapshot()
    required = PRODUCTION_REQUIRED_ENV if snapshot["environment"] == "production" else []
    missing = [name for name in required if not str(os.getenv(name) or "").strip()]
    return {
        "required": required,
        "missing": missing,
        "valid": len(missing) == 0,
    }
