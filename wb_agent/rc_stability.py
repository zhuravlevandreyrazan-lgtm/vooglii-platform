"""Pure read-only Release Candidate stability helpers.

This module summarizes already-collected diagnostics for RC readiness.
It must not call APIs, read/write DB, mutate caches, or start runtimes.
"""

RC_STABILITY_ALLOWED_STATUS = ("READY", "WARNING", "BLOCKED")
RC_STABILITY_ALLOWED_SCHEDULER_STATUS = ("OK", "WARNING", "ERROR", "UNKNOWN")
RC_STABILITY_ALLOWED_RUNTIME_STATUS = ("OK", "WARNING", "ERROR", "UNKNOWN")

__all__ = [
    "RC_STABILITY_ALLOWED_STATUS",
    "RC_STABILITY_ALLOWED_SCHEDULER_STATUS",
    "RC_STABILITY_ALLOWED_RUNTIME_STATUS",
    "build_rc_stability_snapshot",
    "rc_stability_text",
]


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


def _dedup_text(items):
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


def _latency_payload(item):
    item = dict(item or {})
    return {
        "avg_ms": _float_or_none(item.get("avg_ms")),
        "min_ms": _float_or_none(item.get("min_ms")),
        "max_ms": _float_or_none(item.get("max_ms")),
        "p95_ms": _float_or_none(item.get("p95_ms")),
        "failed_count": _int_or_none(item.get("failed_count")) or 0,
        "timeout_count": _int_or_none(item.get("timeout_count")) or 0,
        "iterations": _int_or_none(item.get("iterations")) or 0,
        "mode": str(item.get("mode") or "unknown"),
        "light_path_used": bool(item.get("light_path_used")),
        "warnings": _dedup_text(item.get("warnings")),
    }


def _latency_budget_warnings(command_latency):
    budgets = {
        "director": 2000.0,
        "home": 2000.0,
        "cfo_insights": 1500.0,
        "kpi": 1200.0,
    }
    warnings = []
    for name, budget in budgets.items():
        item = dict((command_latency or {}).get(name) or {})
        p95_ms = _float_or_none(item.get("p95_ms"))
        if p95_ms is not None and p95_ms > budget:
            warnings.append(f"{name} p95 above budget: {p95_ms:.1f} ms > {budget:.0f} ms")
    return warnings


def build_rc_stability_snapshot(
    tested_commands=None,
    command_latency=None,
    memory_baseline_mb=None,
    memory_after_mb=None,
    memory_delta_mb=None,
    request_context_isolated=None,
    duplicate_snapshot_builds=None,
    db_open_count=None,
    api_call_count=None,
    scheduler_status=None,
    telegram_runtime_status=None,
    warnings=None,
    recommendations=None,
    write_attempt_detected=False,
    severe_exceptions=None,
):
    tested_commands = [str(item) for item in list(tested_commands or []) if str(item or "").strip()]
    command_latency = {
        str(name): _latency_payload(payload)
        for name, payload in dict(command_latency or {}).items()
    }
    duplicate_snapshot_builds = list(duplicate_snapshot_builds or [])
    api_call_count = dict(api_call_count or {})
    scheduler_status = dict(scheduler_status or {})
    telegram_runtime_status = dict(telegram_runtime_status or {})
    warnings = _dedup_text(warnings)
    recommendations = _dedup_text(recommendations)
    severe_exceptions = _dedup_text(severe_exceptions)

    scheduler_state = str(scheduler_status.get("scheduler_status") or "UNKNOWN").upper()
    if scheduler_state not in RC_STABILITY_ALLOWED_SCHEDULER_STATUS:
        scheduler_state = "UNKNOWN"
    telegram_state = str(telegram_runtime_status.get("status") or "UNKNOWN").upper()
    if telegram_state not in RC_STABILITY_ALLOWED_RUNTIME_STATUS:
        telegram_state = "UNKNOWN"

    total_failed = sum(int((item or {}).get("failed_count") or 0) for item in command_latency.values())
    total_timeouts = sum(int((item or {}).get("timeout_count") or 0) for item in command_latency.values())
    latency_budget_warnings = _latency_budget_warnings(command_latency)
    warnings.extend(latency_budget_warnings)

    memory_delta = _float_or_none(memory_delta_mb)
    memory_warning = False
    if memory_delta is not None and memory_delta > 25.0:
        warnings.append(f"memory delta is elevated: {memory_delta:.2f} MB")
        memory_warning = True

    if scheduler_state == "UNKNOWN":
        warnings.append("scheduler status unavailable")
    elif scheduler_state == "WARNING":
        warnings.append("scheduler reports warnings")
    elif scheduler_state == "ERROR":
        warnings.append("scheduler reports critical errors")

    finance_api_calls = int(api_call_count.get("finance_api_calls") or 0)
    ads_api_calls = int(api_call_count.get("ads_api_calls") or 0)
    sales_api_calls = int(api_call_count.get("sales_api_calls") or 0)
    if finance_api_calls or ads_api_calls or sales_api_calls:
        warnings.append("unexpected external API calls detected during RC diagnostics")

    if total_timeouts > 0:
        warnings.append(f"readonly stress test timeouts detected: {total_timeouts}")
    if total_failed > 0:
        warnings.append(f"readonly stress test failures detected: {total_failed}")
    if duplicate_snapshot_builds:
        warnings.append("duplicate snapshot builds detected")
    if request_context_isolated is False:
        warnings.append("request-local snapshot context isolation failed")
    if write_attempt_detected:
        warnings.append("write attempt detected during RC diagnostics")
    warnings.extend(severe_exceptions)
    warnings = _dedup_text(warnings)

    if total_failed > 0 or request_context_isolated is False or write_attempt_detected or severe_exceptions or scheduler_state == "ERROR":
        status = "BLOCKED"
    elif latency_budget_warnings or scheduler_state == "UNKNOWN" or memory_warning or duplicate_snapshot_builds:
        status = "WARNING"
    else:
        status = "READY"

    if status == "READY":
        recommendations.append("RC diagnostics look stable enough for release-candidate validation.")
    if latency_budget_warnings:
        recommendations.append("Review slow executive commands before RC sign-off.")
    if scheduler_state == "UNKNOWN":
        recommendations.append("Attach scheduler runtime when validating RC in the live Telegram process.")
    if memory_warning:
        recommendations.append("Repeat memory smoke after longer readonly runs to confirm cache cleanup.")
    if duplicate_snapshot_builds:
        recommendations.append("Inspect snapshot reuse if duplicate builds keep appearing in RC diagnostics.")
    if request_context_isolated is False:
        recommendations.append("Block release until request-local snapshot contexts are isolated again.")
    if total_failed > 0:
        recommendations.append("Block release until readonly stress failures are resolved.")
    recommendations = _dedup_text(recommendations)

    return {
        "status": status,
        "tested_commands": tested_commands,
        "command_latency": command_latency,
        "memory_baseline_mb": _float_or_none(memory_baseline_mb),
        "memory_after_mb": _float_or_none(memory_after_mb),
        "memory_delta_mb": memory_delta,
        "request_context_isolated": bool(request_context_isolated),
        "duplicate_snapshot_builds": duplicate_snapshot_builds,
        "db_open_count": _int_or_none(db_open_count) or 0,
        "api_call_count": {
            "finance_api_calls": finance_api_calls,
            "ads_api_calls": ads_api_calls,
            "sales_api_calls": sales_api_calls,
        },
        "scheduler_status": scheduler_state,
        "scheduler_details": scheduler_status,
        "telegram_runtime_status": telegram_state,
        "telegram_runtime_details": telegram_runtime_status,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def rc_stability_text(snapshot):
    snapshot = dict(snapshot or {})
    command_latency = dict(snapshot.get("command_latency") or {})
    api_call_count = dict(snapshot.get("api_call_count") or {})

    lines = [
        "RELEASE CANDIDATE STATUS",
        "",
        f"Status: {snapshot.get('status') or 'WARNING'}",
        "",
        "Performance:",
    ]
    if command_latency:
        for name in ("director", "home", "advisor_v2", "decision", "cfo_insights", "kpi", "udl", "business_metrics"):
            item = dict(command_latency.get(name) or {})
            if not item:
                continue
            lines.append(
                f"- {name} avg: {float(item.get('avg_ms') or 0.0):.1f} ms | p95: {float(item.get('p95_ms') or 0.0):.1f} ms"
            )
    else:
        lines.append("- no data")

    lines.extend([
        "",
        "Stability:",
        f"- request context isolation: {'OK' if snapshot.get('request_context_isolated') else 'FAILED'}",
        f"- memory delta: {float(snapshot.get('memory_delta_mb') or 0.0):.2f} MB",
        f"- duplicate snapshot builds: {len(list(snapshot.get('duplicate_snapshot_builds') or []))}",
        f"- DB opens: {int(snapshot.get('db_open_count') or 0)}",
        f"- API calls: finance={int(api_call_count.get('finance_api_calls') or 0)}, ads={int(api_call_count.get('ads_api_calls') or 0)}, sales={int(api_call_count.get('sales_api_calls') or 0)}",
        "",
        "Scheduler:",
        f"- status: {snapshot.get('scheduler_status') or 'UNKNOWN'}",
        "",
        "Telegram Runtime:",
        f"- status: {snapshot.get('telegram_runtime_status') or 'UNKNOWN'}",
        "",
        "Recommendations:",
    ])
    recommendations = list(snapshot.get("recommendations") or [])
    if recommendations:
        for item in recommendations:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    warnings = list(snapshot.get("warnings") or [])
    lines.extend(["", "Warnings:"])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    return "\n".join(lines)
