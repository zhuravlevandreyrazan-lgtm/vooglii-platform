"""Pure read-only Control Center helpers."""

from __future__ import annotations

CONTROL_CENTER_ALLOWED_STATUS = ("READY", "WARNING", "BLOCKED")

__all__ = [
    "CONTROL_CENTER_ALLOWED_STATUS",
    "build_control_center_snapshot",
    "control_center_text",
]


def _text(value, default="UNKNOWN"):
    text = str(value or "").strip()
    return text if text else default


def _list_text(items):
    result = []
    seen = set()
    for item in list(items or []):
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _float_or_none(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _int_or_none(value):
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _status_bucket(*values):
    normalized = [_text(value) for value in values]
    if any(value in ("BLOCKED", "ERROR", "CRITICAL") for value in normalized):
        return "BLOCKED"
    if any(value in ("WARNING", "PARTIAL", "UNKNOWN", "WAITING_FINANCE_API", "ALMOST_READY", "MIGRATED_PARTIAL") for value in normalized):
        return "WARNING"
    return "READY"


def build_control_center_snapshot(
    product_readiness_snapshot=None,
    rc_stability_snapshot=None,
    performance_snapshot=None,
    system_audit_snapshot=None,
    command_audit_snapshot=None,
    migration_readiness_snapshot=None,
    finance_api_status_snapshot=None,
    director_snapshot=None,
    kpi_snapshot=None,
    cfo_insights_snapshot=None,
    decision_snapshot=None,
    advisor_v2_snapshot=None,
    sku_registry_snapshot=None,
    legacy_gold_validation_snapshot=None,
):
    product_readiness_snapshot = dict(product_readiness_snapshot or {})
    rc_stability_snapshot = dict(rc_stability_snapshot or {})
    performance_snapshot = dict(performance_snapshot or {})
    system_audit_snapshot = dict(system_audit_snapshot or {})
    command_audit_snapshot = dict(command_audit_snapshot or {})
    migration_readiness_snapshot = dict(migration_readiness_snapshot or {})
    finance_api_status_snapshot = dict(finance_api_status_snapshot or {})
    director_snapshot = dict(director_snapshot or {})
    kpi_snapshot = dict(kpi_snapshot or {})
    cfo_insights_snapshot = dict(cfo_insights_snapshot or {})
    decision_snapshot = dict(decision_snapshot or {})
    advisor_v2_snapshot = dict(advisor_v2_snapshot or {})
    sku_registry_snapshot = dict(sku_registry_snapshot or {})
    legacy_gold_validation_snapshot = dict(legacy_gold_validation_snapshot or {})

    product = {
        "product_status": _text(product_readiness_snapshot.get("product_status")),
        "primary_entrypoint": _text(product_readiness_snapshot.get("primary_entrypoint"), "/director"),
        "director_ready": bool(product_readiness_snapshot.get("director_ready")),
        "advisor_v2_ready": bool(product_readiness_snapshot.get("advisor_v2_ready")),
        "rc_status": _text(rc_stability_snapshot.get("status")),
    }

    architecture = {
        "core_v2_status": "READY",
        "financial_engine_status": _text((((system_audit_snapshot.get("financial_engine_snapshot") or {}).get("status")))),
        "business_metrics_status": _text((((system_audit_snapshot.get("business_metrics_snapshot") or {}).get("official_status")))),
        "udl_status": _text(system_audit_snapshot.get("udl_status")),
        "kpi_status": _text(kpi_snapshot.get("status")),
        "cfo_status": _text(cfo_insights_snapshot.get("status")),
        "decision_status": _text(decision_snapshot.get("status")),
        "director_status": _text(director_snapshot.get("status")),
    }

    director_latency_ms = _float_or_none(performance_snapshot.get("total_ms"))
    director_budget_status = "UNKNOWN"
    budget_ms = _float_or_none(performance_snapshot.get("budget_ms"))
    if director_latency_ms is not None:
        if budget_ms is not None and director_latency_ms > budget_ms:
            director_budget_status = "OVER_BUDGET"
        else:
            director_budget_status = "WITHIN_BUDGET"

    performance = {
        "director_latency_ms": director_latency_ms,
        "director_budget_status": director_budget_status,
        "duplicate_snapshot_builds": list(performance_snapshot.get("duplicate_snapshot_builds") or []),
        "db_open_count": _int_or_none(performance_snapshot.get("db_open_count")) or 0,
        "db_query_count": _int_or_none(performance_snapshot.get("db_query_count")) or 0,
        "performance_status": _text(performance_snapshot.get("status")),
    }

    detected_issue = _text(finance_api_status_snapshot.get("detected_issue"), "UNKNOWN")
    finance_runtime_status = _text(finance_api_status_snapshot.get("status"))
    legacy_gold_validation_status = _text(legacy_gold_validation_snapshot.get("legacy_gold_validation_status"), "NOT_APPLICABLE")
    legacy_fallback_available = bool(legacy_gold_validation_snapshot.get("legacy_estimate_available")) or _text(legacy_gold_validation_snapshot.get("status")) == "LEGACY_FALLBACK"
    legacy_finance_status = "not checked"
    if legacy_fallback_available:
        legacy_finance_status = "available"
    elif finance_runtime_status == "RATE_LIMIT":
        legacy_finance_status = "rate limited"
    finance_blocker = "none"
    if finance_runtime_status == "FORBIDDEN" and detected_issue == "TOKEN_CATEGORY_REQUIRED":
        finance_blocker = "token compatibility"
    elif finance_runtime_status in ("RATE_LIMIT", "UNAVAILABLE", "UNAUTHORIZED"):
        finance_blocker = finance_runtime_status.lower()

    finance = {
        "new_finance_api_status": finance_runtime_status,
        "new_finance_api_issue": detected_issue,
        "legacy_finance_status": legacy_finance_status,
        "legacy_fallback_available": legacy_fallback_available,
        "legacy_gold_validation_status": legacy_gold_validation_status,
        "official_finance_available": bool(legacy_gold_validation_snapshot.get("official_new_finance_available")),
        "finance_blocker": finance_blocker,
    }

    system_quality = dict(system_audit_snapshot.get("quality") or {})
    system_health = dict(system_audit_snapshot.get("health") or {})
    finance_health = dict(system_audit_snapshot.get("finance_health") or {})
    data = {
        "sales_status": _text(((system_quality.get("sales") or {}).get("status"))),
        "ads_status": _text((system_audit_snapshot.get("ads_health") or {}).get("status")),
        "payment_status": _text((((system_audit_snapshot.get("udl_snapshot") or {}).get("payments") or {}).get("status"))),
        "sku_registry_status": _text(sku_registry_snapshot.get("registry_status")),
        "cost_coverage": _float_or_none((legacy_gold_validation_snapshot.get("cost_coverage_percent"))),
        "data_quality_status": _text(system_quality.get("overall_status")),
        "trust_score": _int_or_none(system_audit_snapshot.get("trust_score")),
    }

    business = {
        "director_status": _text(director_snapshot.get("status")),
        "advisor_v2_status": _text(advisor_v2_snapshot.get("status")),
        "cfo_status": _text(cfo_insights_snapshot.get("status")),
        "decision_status": _text(decision_snapshot.get("status")),
        "kpi_status": _text(kpi_snapshot.get("status")),
        "business_health": _text(director_snapshot.get("business_health")),
    }

    diagnostics = {
        "system_audit_status": _text(system_health.get("verdict")),
        "command_audit_status": _text(command_audit_snapshot.get("status")),
        "migration_readiness_status": _text(migration_readiness_snapshot.get("status")),
        "rc_stability_status": _text(rc_stability_snapshot.get("status")),
        "product_readiness_status": _text(product_readiness_snapshot.get("product_status")),
    }

    tests = {
        "smoke_status": "last known: tests pass via developer run",
        "scenario_status": "last known: tests pass via developer run",
        "consistency_status": "last known: tests pass via developer run",
        "readonly_status": "last known: tests pass via developer run",
        "gold_standard_status": "last known: tests pass via developer run",
    }

    known_blockers = []
    if finance_runtime_status == "FORBIDDEN" and detected_issue == "TOKEN_CATEGORY_REQUIRED":
        known_blockers.append("New Finance API is blocked by token compatibility.")
    if finance_runtime_status == "RATE_LIMIT":
        known_blockers.append("Finance API is under cooldown / rate limit.")
    if legacy_gold_validation_status == "NEEDS_REVIEW":
        known_blockers.append("Legacy fallback does not match Gold Standard yet.")
    known_blockers.extend(_list_text(product_readiness_snapshot.get("remaining_blockers")))
    known_blockers.extend(_list_text(rc_stability_snapshot.get("warnings")))
    known_blockers = _list_text(known_blockers)[:12]

    status = _status_bucket(
        product.get("product_status"),
        rc_stability_snapshot.get("status"),
        "WARNING" if known_blockers else "READY",
    )
    recommended_next_step = _text(product_readiness_snapshot.get("recommended_next_step"), "Keep Director as the primary entrypoint and continue read-only validation.")
    if legacy_gold_validation_status == "MATCHED_LEGACY":
        recommended_next_step = "Wait for the new Finance API token migration and keep legacy fallback only for verification."
    elif legacy_gold_validation_status == "NEEDS_REVIEW":
        recommended_next_step = "Review legacy fallback row normalization before using May legacy validation as a confidence signal."

    warnings = _list_text(
        list(performance_snapshot.get("warnings") or [])
        + list(system_audit_snapshot.get("warnings") or [])
        + list(cfo_insights_snapshot.get("warnings") or [])
    )[:20]

    return {
        "status": status,
        "product": product,
        "architecture": architecture,
        "performance": performance,
        "finance": finance,
        "data": data,
        "business": business,
        "diagnostics": diagnostics,
        "tests": tests,
        "known_blockers": known_blockers,
        "recommended_next_step": recommended_next_step,
        "warnings": warnings,
    }


def control_center_text(snapshot):
    snapshot = dict(snapshot or {})
    product = dict(snapshot.get("product") or {})
    architecture = dict(snapshot.get("architecture") or {})
    performance = dict(snapshot.get("performance") or {})
    finance = dict(snapshot.get("finance") or {})
    data = dict(snapshot.get("data") or {})
    business = dict(snapshot.get("business") or {})
    diagnostics = dict(snapshot.get("diagnostics") or {})
    known_blockers = list(snapshot.get("known_blockers") or [])

    lines = [
        "WB AGENT CONTROL CENTER",
        "",
        f'Overall status: {snapshot.get("status") or "WARNING"}',
        "",
        "Product",
        f'- Primary entrypoint: {product.get("primary_entrypoint") or "/director"}',
        f'- Product readiness: {product.get("product_status") or "UNKNOWN"}',
        f'- RC status: {product.get("rc_status") or "UNKNOWN"}',
        "",
        "Architecture",
        f'- Core v2: {architecture.get("core_v2_status") or "UNKNOWN"}',
        f'- Financial Engine: {architecture.get("financial_engine_status") or "UNKNOWN"}',
        f'- UDL: {architecture.get("udl_status") or "UNKNOWN"}',
        f'- KPI: {architecture.get("kpi_status") or "UNKNOWN"}',
        f'- CFO: {architecture.get("cfo_status") or "UNKNOWN"}',
        f'- Decision: {architecture.get("decision_status") or "UNKNOWN"}',
        f'- Director: {architecture.get("director_status") or "UNKNOWN"}',
        "",
        "Finance",
        f'- New Finance API: {finance.get("new_finance_api_status") or "UNKNOWN"}',
        f'- Legacy finance API: {finance.get("legacy_finance_status") or "unknown"}',
        f'- Legacy Gold Standard: {finance.get("legacy_gold_validation_status") or "NOT_APPLICABLE"}',
        f'- Official finance: {"available" if finance.get("official_finance_available") else "not available"}',
        "",
        "Data",
        f'- Sales: {data.get("sales_status") or "UNKNOWN"}',
        f'- Ads: {data.get("ads_status") or "UNKNOWN"}',
        f'- Payments: {data.get("payment_status") or "UNKNOWN"}',
        f'- SKU Registry: {data.get("sku_registry_status") or "UNKNOWN"}',
        f'- Data quality: {data.get("data_quality_status") or "UNKNOWN"}',
        "",
        "Performance",
        f'- Director latency: {float(performance.get("director_latency_ms") or 0.0):.1f} ms' if performance.get("director_latency_ms") is not None else "- Director latency: unknown",
        f'- Budget: {performance.get("director_budget_status") or "UNKNOWN"}',
        f'- Duplicate builds: {len(list(performance.get("duplicate_snapshot_builds") or []))}',
        f'- DB opens / queries: {int(performance.get("db_open_count") or 0)} / {int(performance.get("db_query_count") or 0)}',
        "",
        "Business",
        f'- Director: {business.get("director_status") or "UNKNOWN"}',
        f'- Advisor v2: {business.get("advisor_v2_status") or "UNKNOWN"}',
        f'- CFO Insights: {business.get("cfo_status") or "UNKNOWN"}',
        f'- Decision Engine: {business.get("decision_status") or "UNKNOWN"}',
        "",
        "Diagnostics",
        f'- System Audit: {diagnostics.get("system_audit_status") or "UNKNOWN"}',
        f'- RC Stability: {diagnostics.get("rc_stability_status") or "UNKNOWN"}',
        f'- Product Readiness: {diagnostics.get("product_readiness_status") or "UNKNOWN"}',
        "",
        "Known blockers",
    ]
    if known_blockers:
        for index, item in enumerate(known_blockers[:8], 1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("1. none")
    lines.extend([
        "",
        "Recommended next step",
        str(snapshot.get("recommended_next_step") or "-"),
    ])
    return "\n".join(lines)
