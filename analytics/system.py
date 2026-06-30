from __future__ import annotations

from typing import Any

from analytics.cache import get_cache_status, get_stale_cache_value
from analytics.build_info import get_build_info
from analytics.common import API_VERSION, BUILD_VERSION, DEFAULT_USER_ID, PRODUCT_NAME, git_revision, now_iso, safe_text, status_to_api
from analytics.env import get_environment_snapshot
from analytics.performance import get_performance_snapshot, get_slow_endpoints


STATUS_BUDGETS_MS = {
    "/api/health": 500,
    "/api/version": 500,
    "/api/status": 500,
    "/api/command-center": 5000,
    "/api/executive": 5000,
    "/api/advisor": 5000,
    "/api/reports": 5000,
    "/api/system": 5000,
    "/api/business": 10000,
    "/api/finance": 10000,
    "/api/advertising": 10000,
    "/api/products": 10000,
    "/api/inventory": 10000,
}


def _latest_runtime(key: str) -> dict[str, Any]:
    payload = get_stale_cache_value(key) or {}
    return dict(payload.get("runtime") or {})


def _last_updated_for(cache_key: str, *field_names: str) -> str | None:
    payload = get_stale_cache_value(cache_key) or {}
    for field_name in field_names:
        value = payload.get(field_name)
        if value:
            return str(value)
    return None


def _endpoint_diagnostics() -> dict[str, Any]:
    performance = get_performance_snapshot()
    diagnostics = {}
    for endpoint, stats in performance.items():
        diagnostics[endpoint] = {
            "last_duration_ms": stats.get("last_duration_ms"),
            "last_source": stats.get("last_source"),
            "last_cached": bool(stats.get("last_cached")),
            "last_stale": bool(stats.get("last_stale")),
            "last_degraded": bool(stats.get("last_degraded")),
            "last_error": stats.get("last_error"),
            "last_success_at": stats.get("last_success_at"),
        }
    return diagnostics


def get_system_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    del user_id
    performance = get_performance_snapshot()
    cache = get_cache_status()
    finance_payload = get_stale_cache_value("finance") or {}
    advertising_payload = get_stale_cache_value("advertising") or {}
    executive_payload = get_stale_cache_value("executive") or {}
    business_payload = get_stale_cache_value("business") or {}

    finance_summary = dict(finance_payload.get("summary") or {})
    advertising_summary = dict(advertising_payload.get("summary") or {})
    executive_system = dict(executive_payload.get("system") or {})
    business_summary = dict(business_payload.get("summary") or {})
    slow_endpoints = get_slow_endpoints(STATUS_BUDGETS_MS)
    last_errors = {
        endpoint: {
            "message": stats.get("last_error"),
            "at": stats.get("last_error_at"),
        }
        for endpoint, stats in performance.items()
        if stats.get("last_error")
    }
    health = {
        "verdict": "WARNING" if last_errors else "GOOD",
        "slow_endpoints": len(slow_endpoints),
        "cached_snapshots": cache.get("size", 0),
    }
    quality = {
        "analytics_runtime": "stable" if performance else "warming_up",
        "cache_hit_ratio": cache.get("stats", {}),
        "executive_source": _latest_runtime("executive").get("source"),
        "advisor_source": _latest_runtime("advisor").get("source"),
    }

    return {
        "product": PRODUCT_NAME,
        "mode": "read_only",
        "status": safe_text(health.get("verdict"), "UNKNOWN"),
        "health": health,
        "quality": quality,
        "adsHealth": {
            "status": safe_text(advertising_summary.get("adsHealth"), "UNKNOWN"),
            "lastRuntime": _latest_runtime("advertising"),
        },
        "financeHealth": {
            "status": safe_text(finance_summary.get("health"), "UNKNOWN"),
            "trustScore": finance_summary.get("trustScore"),
            "lastRuntime": _latest_runtime("finance"),
        },
        "cache": cache,
        "writeSafety": {
            "mode": "read_only",
            "telegram_mutations": "disabled",
        },
        "cooldowns": {
            "heavy_endpoints": "protected_by_timeout",
            "cache_ttl_seconds": {
                "executive": 120,
                "advisor": 120,
                "reports": 120,
                "system": 120,
                "business": 180,
                "finance": 180,
                "advertising": 180,
                "products": 180,
                "inventory": 180,
            },
        },
        "lastUpdates": {
            "business": _last_updated_for("business", "generatedAt"),
            "finance": _last_updated_for("finance", "lastUpdated"),
            "advertising": _last_updated_for("advertising", "lastUpdated"),
            "products": _last_updated_for("products", "lastUpdated"),
            "inventory": _last_updated_for("inventory", "lastUpdated"),
            "advisor": _last_updated_for("advisor", "lastUpdated"),
            "reports": _last_updated_for("reports", "lastUpdated"),
            "executive": executive_system.get("last_updated"),
        },
        "coreV2Status": {
            "version": BUILD_VERSION,
            "api": API_VERSION,
            "runtime": "fast_mode",
        },
        "controlCenter": {
            "status": safe_text((executive_payload.get("business_health") or {}).get("status"), "UNKNOWN"),
            "summary": safe_text((executive_payload.get("business_health") or {}).get("summary"), "Command Center cache is warming up."),
            "lastRuntime": _latest_runtime("executive"),
        },
        "financeApi": {
            "status": safe_text(finance_summary.get("health"), "UNKNOWN"),
            "mode": safe_text((finance_payload.get("quality") or {}).get("residualUsage"), "UNKNOWN"),
            "lastRuntime": _latest_runtime("finance"),
        },
        "lastUpdated": now_iso(),
        "database": {
            "status": "GOOD",
            "mode": "shared_runtime",
        },
        "apiStatus": {
            "status": "GOOD",
            "slowEndpoints": slow_endpoints,
            "endpointDiagnostics": _endpoint_diagnostics(),
            "lastErrors": last_errors,
        },
        "businessSnapshot": {
            "revenue": business_summary.get("revenue"),
            "profit": business_summary.get("profit"),
            "lastRuntime": _latest_runtime("business"),
        },
    }


def get_status_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    del user_id
    performance = get_performance_snapshot()
    cache = get_cache_status()
    analytics_state = "GOOD" if performance else "UNKNOWN"
    last_successful_snapshot = {
        endpoint: str(stats.get("last_success_at") or "")
        for endpoint, stats in performance.items()
        if stats.get("last_success_at")
    }
    last_error = {
        endpoint: {
            "message": stats.get("last_error"),
            "at": stats.get("last_error_at"),
        }
        for endpoint, stats in performance.items()
        if stats.get("last_error")
    }
    system_state = "WARNING" if last_error else analytics_state
    system_payload = get_stale_cache_value("system") or {}
    finance_payload = get_stale_cache_value("finance") or {}
    advertising_payload = get_stale_cache_value("advertising") or {}
    wb_api_state = status_to_api(((system_payload.get("financeApi") or {}).get("status")))
    finance_state = status_to_api(((finance_payload.get("summary") or {}).get("health")))
    ads_state = status_to_api(((advertising_payload.get("summary") or {}).get("adsHealth")))
    if wb_api_state == "UNKNOWN" and "/api/system" in performance:
        wb_api_state = "WARNING" if (performance.get("/api/system") or {}).get("last_error") else "GOOD"
    if finance_state == "UNKNOWN" and "/api/finance" in performance:
        finance_state = "WARNING" if (performance.get("/api/finance") or {}).get("last_error") else "GOOD"
    if ads_state == "UNKNOWN" and "/api/advertising" in performance:
        ads_state = "WARNING" if (performance.get("/api/advertising") or {}).get("last_error") else "GOOD"
    build_info = get_build_info()
    environment = get_environment_snapshot()

    return {
        "status": "ok",
        "wbApi": wb_api_state,
        "database": "GOOD",
        "analytics": analytics_state,
        "ads": ads_state,
        "finance": finance_state,
        "system": system_state,
        "cache": cache,
        "slowEndpoints": get_slow_endpoints(STATUS_BUDGETS_MS),
        "lastSuccessfulSnapshot": last_successful_snapshot,
        "lastError": last_error,
        "endpoints": _endpoint_diagnostics(),
        "version": BUILD_VERSION,
        "build": now_iso(),
        "buildInfo": build_info,
        "environment": environment,
        "timestamp": now_iso(),
    }


def get_version_payload() -> dict[str, Any]:
    payload = get_build_info()
    return {
        "version": payload["version"],
        "build": payload["buildTimestamp"],
        "git": payload["git"],
        "apiVersion": API_VERSION,
        "environment": payload["environment"],
        "buildType": payload["buildType"],
        "frontendVersion": payload["frontendVersion"],
    }
