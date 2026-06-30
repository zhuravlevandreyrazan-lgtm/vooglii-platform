from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_server import app


CORE_ENDPOINTS = [
    "/api/health",
    "/api/metrics",
    "/api/version",
    "/api/status",
    "/api/auth/session",
    "/api/auth/profile",
    "/api/organization",
    "/api/wb-cabinet",
    "/api/organizations",
    "/api/organizations/org_vooglii_demo",
    "/api/wb-cabinets",
    "/api/wb-cabinets/cabinet_vooglii_main",
    "/api/workspace/context",
]
STABLE_ENDPOINTS = [
    "/api/business",
    "/api/finance",
    "/api/advertising",
    "/api/products",
    "/api/inventory",
]
DERIVED_ENDPOINTS = [
    "/api/command-center",
    "/api/executive",
    "/api/advisor",
    "/api/reports",
    "/api/system",
    "/api/exports",
    "/api/schedules",
    "/api/jobs",
    "/api/notifications",
    "/api/notifications/rules",
    "/api/notifications/history",
    "/api/notifications/channels",
]


def _cell(value: object, width: int) -> str:
    return str(value).ljust(width)


def _run_endpoint(client: TestClient, endpoint: str) -> dict[str, object]:
    started_at = time.perf_counter()
    response = client.get(endpoint)
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
    payload = response.json()
    runtime = payload.get("runtime") or {}
    return {
        "endpoint": endpoint,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "source": runtime.get("source", "-"),
        "cached": runtime.get("cached", "-"),
        "degraded": runtime.get("degraded", "-"),
        "payload": payload,
    }


def _run_mutation(
    client: TestClient,
    method: str,
    endpoint: str,
    body: dict[str, object] | None = None,
) -> dict[str, object]:
    started_at = time.perf_counter()
    response = client.request(method, endpoint, json=body)
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
    payload = response.json()
    runtime = payload.get("runtime") or {}
    return {
        "endpoint": f"{method} {endpoint}",
        "status": response.status_code,
        "duration_ms": duration_ms,
        "source": runtime.get("source", "-"),
        "cached": runtime.get("cached", "-"),
        "degraded": runtime.get("degraded", "-"),
        "payload": payload,
    }


def _print_table(title: str, rows: list[dict[str, object]]) -> None:
    headers = ("endpoint", "status", "duration_ms", "source", "cached", "degraded")
    widths = (42, 8, 14, 14, 8, 10)
    print(f"\n{title}")
    print(" ".join(_cell(label, width) for label, width in zip(headers, widths)))
    print(" ".join("-" * width for width in widths))
    for row in rows:
        print(
            " ".join(
                (
                    _cell(row["endpoint"], widths[0]),
                    _cell(row["status"], widths[1]),
                    _cell(row["duration_ms"], widths[2]),
                    _cell(row["source"], widths[3]),
                    _cell(row["cached"], widths[4]),
                    _cell(row["degraded"], widths[5]),
                )
            )
        )


def main() -> int:
    client = TestClient(app)
    primary_rows: list[dict[str, object]] = []

    try:
        for endpoint in CORE_ENDPOINTS + STABLE_ENDPOINTS + DERIVED_ENDPOINTS:
            primary_rows.append(_run_endpoint(client, endpoint))
    except Exception as exc:
        print(f"Smoke API failed before JSON response: {exc}")
        return 1

    cache_rows: list[dict[str, object]] = []
    try:
        for endpoint in STABLE_ENDPOINTS:
            cache_rows.append(_run_endpoint(client, endpoint))
    except Exception as exc:
        print(f"Stable endpoint cache verification failed: {exc}")
        return 1

    mutation_rows: list[dict[str, object]] = []
    try:
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/advisor/query",
                {"message": "What should I do today?", "context": {"workspace": "advisor"}},
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/exports",
                {"workspace": "finance", "format": "CSV", "name": "Smoke Finance Export"},
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/schedules",
                {
                    "name": "Smoke Schedule",
                    "workspace": "reports",
                    "time": "11:30",
                    "timezone": "Europe/Moscow",
                    "cadence": "weekly",
                    "format": "JSON",
                    "enabled": True,
                },
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "PATCH",
                "/api/schedules/schedule_ceo_daily",
                {"enabled": False},
            )
        )
        mutation_rows.append(_run_mutation(client, "DELETE", "/api/schedules/schedule_advisor_digest"))
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/notifications/rules",
                {
                    "name": "Smoke Notification Rule",
                    "enabled": True,
                    "channel": "in_app",
                    "severity": "info",
                    "trigger": "Smoke test trigger",
                    "schedule": "On demand",
                    "owner": "Smoke Runner",
                    "deepLink": "/notifications",
                },
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "PATCH",
                "/api/notifications/rules/notification_rule_001",
                {"enabled": False},
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "DELETE",
                "/api/notifications/rules/notification_rule_005",
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/notifications/test",
                {"channel": "in_app", "message": "Smoke test notification"},
            )
        )
        mutation_rows.append(_run_mutation(client, "POST", "/api/wb-cabinet/connect"))
        mutation_rows.append(_run_mutation(client, "POST", "/api/wb-cabinet/disconnect"))
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/organizations/select",
                {"organizationId": "org_test_seller"},
            )
        )
        mutation_rows.append(
            _run_mutation(
                client,
                "POST",
                "/api/wb-cabinets/select",
                {"cabinetId": "cabinet_test_fashion"},
            )
        )
    except Exception as exc:
        print(f"Mutation endpoint verification failed: {exc}")
        return 1

    _print_table("Primary Run", primary_rows)
    _print_table("Stable Endpoint Cache Verification", cache_rows)
    _print_table("Mutation Verification", mutation_rows)

    for row in primary_rows:
        if row["endpoint"] in CORE_ENDPOINTS and row["status"] != 200:
            return 1
        payload = row["payload"]
        if row["endpoint"] == "/api/health":
            if not isinstance(payload.get("uptimeSeconds"), (int, float)):
                return 1
        if row["endpoint"] == "/api/version":
            if not isinstance(payload.get("environment"), str) or not isinstance(payload.get("buildType"), str):
                return 1
        if row["endpoint"] == "/api/metrics":
            if not isinstance(payload.get("startupValidation"), dict):
                return 1

    for row in mutation_rows:
        payload = row["payload"]
        if row["status"] != 200 or not isinstance(payload, dict):
            return 1
        endpoint = str(row["endpoint"])
        if endpoint.startswith("POST /api/advisor/query"):
            if payload.get("status") not in {"ok", "degraded"}:
                return 1
        elif endpoint.startswith("POST /api/exports"):
            if not isinstance(payload.get("export"), dict):
                return 1
        elif endpoint.startswith(("POST /api/schedules", "PATCH /api/schedules", "DELETE /api/schedules")):
            if not isinstance(payload.get("schedule"), dict):
                return 1
        elif endpoint.startswith(("POST /api/notifications/rules", "PATCH /api/notifications/rules", "DELETE /api/notifications/rules")):
            if not isinstance(payload.get("rule"), dict):
                return 1
        elif endpoint.startswith("POST /api/notifications/test"):
            if not isinstance(payload.get("delivery"), dict):
                return 1
        elif endpoint.startswith("POST /api/wb-cabinet"):
            cabinet = payload.get("cabinet")
            if not isinstance(cabinet, dict) or not isinstance(cabinet.get("connected"), bool):
                return 1
        elif endpoint.startswith(("POST /api/organizations/select", "POST /api/wb-cabinets/select")):
            if not isinstance(payload.get("organizationId"), str) or not isinstance(payload.get("cabinetId"), str):
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
