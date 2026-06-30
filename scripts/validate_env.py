from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_KEYS = [
    "APP_ENV",
    "BUILD_TIMESTAMP",
    "API_HOST",
    "API_PORT",
    "FRONTEND_PORT",
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_APP_ENV",
    "ALLOWED_ORIGINS",
    "TRUSTED_HOSTS",
    "LOG_LEVEL",
    "DEMO_MODE_ALLOWED",
    "REQUIRE_TOKENS",
    "API_TIMEOUT_MS",
    "HEALTH_TIMEOUT_MS",
    "BOT_TOKEN",
    "BOT_USERNAME",
    "ADMIN_IDS",
    "WB_TOKEN",
    "WB_STATISTICS_TOKEN",
    "WB_ADVERTISING_TOKEN",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_URI",
    "REDIS_URI",
]

OPTIONAL_KEYS = [
    "PAYMENT_PROVIDER_TOKEN",
    "POSTGRES_URL",
    "REDIS_URL",
]

PLACEHOLDER_PATTERNS = [
    "replace_me",
    "change_me",
    "example.com",
    "strong_password",
]


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def mask_value(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "<empty>"
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"


def contains_placeholder(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    return any(pattern in lowered for pattern in PLACEHOLDER_PATTERNS)


def require(values: dict[str, str], errors: list[str]) -> None:
    for key in REQUIRED_KEYS:
        if not str(values.get(key) or "").strip():
            errors.append(f"Missing required variable: {key}")


def validate_domains(values: dict[str, str], errors: list[str]) -> None:
    api_base = str(values.get("NEXT_PUBLIC_API_BASE_URL") or "")
    origins = {item.strip() for item in str(values.get("ALLOWED_ORIGINS") or "").split(",") if item.strip()}
    hosts = {item.strip() for item in str(values.get("TRUSTED_HOSTS") or "").split(",") if item.strip()}

    if values.get("APP_ENV") == "production":
        if api_base != "https://api.vooglii.ru":
            errors.append("NEXT_PUBLIC_API_BASE_URL must be https://api.vooglii.ru in production.")
        if "https://vooglii.ru" not in origins or "https://www.vooglii.ru" not in origins:
            errors.append("ALLOWED_ORIGINS must include https://vooglii.ru and https://www.vooglii.ru.")
        expected_hosts = {"vooglii.ru", "www.vooglii.ru", "api.vooglii.ru"}
        if not expected_hosts.issubset(hosts):
            errors.append("TRUSTED_HOSTS must include vooglii.ru, www.vooglii.ru, and api.vooglii.ru.")


def validate_postgres(values: dict[str, str], errors: list[str]) -> None:
    user = str(values.get("POSTGRES_USER") or "")
    password = str(values.get("POSTGRES_PASSWORD") or "")
    database = str(values.get("POSTGRES_DB") or "")
    uri = str(values.get("POSTGRES_URI") or "")
    alias = str(values.get("POSTGRES_URL") or "")

    parsed = urlparse(uri)
    if parsed.scheme not in {"postgresql", "postgres"}:
        errors.append("POSTGRES_URI must use postgres/postgresql scheme.")
        return

    expected_netloc = f"{user}:{password}@postgres:5432"
    if parsed.netloc != expected_netloc or parsed.path != f"/{database}":
        errors.append("POSTGRES_URI must match POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB and service postgres.")

    if alias and alias not in {"${POSTGRES_URI}", uri}:
        errors.append("POSTGRES_URL must match POSTGRES_URI or reference ${POSTGRES_URI}.")


def validate_redis(values: dict[str, str], errors: list[str]) -> None:
    uri = str(values.get("REDIS_URI") or "")
    alias = str(values.get("REDIS_URL") or "")
    if uri != "redis://redis:6379/0":
        errors.append("REDIS_URI must point to redis://redis:6379/0.")
    if alias and alias not in {"${REDIS_URI}", uri}:
        errors.append("REDIS_URL must match REDIS_URI or reference ${REDIS_URI}.")


def validate_flags(values: dict[str, str], errors: list[str]) -> None:
    if values.get("APP_ENV") == "production":
        expected = {
            "NEXT_PUBLIC_APP_ENV": "production",
            "DEMO_MODE_ALLOWED": "false",
            "REQUIRE_TOKENS": "true",
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            "FRONTEND_PORT": "3000",
        }
        for key, expected_value in expected.items():
            if str(values.get(key) or "") != expected_value:
                errors.append(f"{key} must be {expected_value} in production.")


def validate_placeholders(values: dict[str, str], warnings: list[str]) -> None:
    for key, value in values.items():
        if contains_placeholder(value):
            warnings.append(f"{key} still contains a placeholder: {mask_value(value)}")


def validate_admin_ids(values: dict[str, str], errors: list[str]) -> None:
    admin_ids = str(values.get("ADMIN_IDS") or "")
    if not re.fullmatch(r"\d+(,\d+)*", admin_ids.replace(" ", "")):
        errors.append("ADMIN_IDS must be a comma-separated list of numeric Telegram IDs.")


def main(argv: list[str]) -> int:
    requested = Path(argv[1]) if len(argv) > 1 else Path(".env.production")
    env_path = requested if requested.exists() else Path(".env.example")
    if not env_path.exists():
        print("ERROR: no env file found. Expected .env.production or .env.example")
        return 1

    values = load_env_file(env_path)
    errors: list[str] = []
    warnings: list[str] = []

    require(values, errors)
    validate_flags(values, errors)
    validate_domains(values, errors)
    validate_postgres(values, errors)
    validate_redis(values, errors)
    validate_admin_ids(values, errors)
    validate_placeholders(values, warnings)

    print(f"Validated: {env_path}")
    print(f"Required keys checked: {len(REQUIRED_KEYS)}")
    print(f"Optional keys recognized: {', '.join(OPTIONAL_KEYS)}")

    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("Errors:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Environment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
