"""Read-only health and system audit text helpers.

This module contains only pure helpers that accept prepared snapshots and
return text lines. No SQL, API calls, filesystem checks, or metric
calculations live here.
"""

from wb_agent.finance_debug import finance_debug_lines
from wb_agent.formatting import money

__all__ = [
    "data_quality_lines",
    "health_lines",
    "system_audit_lines",
]


def data_quality_lines(snapshot):
    snapshot = snapshot or {}
    return [
        f'DATA QUALITY ({snapshot["period_start"]} - {snapshot["period_end"]})',
        "",
        "SALES QUALITY",
        f'sales rows: {int((snapshot.get("sales") or {}).get("rows") or 0)}',
        f'sales min_date: {((snapshot.get("sales") or {}).get("min_date") or "-")}',
        f'sales max_date: {((snapshot.get("sales") or {}).get("max_date") or "-")}',
        f'days covered: {int((snapshot.get("sales") or {}).get("days_covered") or 0)}',
        f'requested days: {int((snapshot.get("sales") or {}).get("requested_days") or 0)}',
        f'missing days: {", ".join(((snapshot.get("sales") or {}).get("missing_days") or [])[:15]) or "-"}',
        f'coverage %: {float((snapshot.get("sales") or {}).get("coverage_percent") or 0):.1f}',
        f'status: {((snapshot.get("sales") or {}).get("status") or "-")}',
        "",
        "ORDERS QUALITY",
        f'orders rows: {int((snapshot.get("orders") or {}).get("rows") or 0)}',
        f'orders min_date: {((snapshot.get("orders") or {}).get("min_date") or "-")}',
        f'orders max_date: {((snapshot.get("orders") or {}).get("max_date") or "-")}',
        f'days covered: {int((snapshot.get("orders") or {}).get("days_covered") or 0)}',
        f'missing days: {", ".join(((snapshot.get("orders") or {}).get("missing_days") or [])[:15]) or "-"}',
        f'coverage %: {float((snapshot.get("orders") or {}).get("coverage_percent") or 0):.1f}',
        f'status: {((snapshot.get("orders") or {}).get("status") or "-")}',
        "",
        "ADVERTISING QUALITY",
        f'advertising rows: {int((snapshot.get("advertising") or {}).get("rows") or 0)}',
        f'advertising min_date: {((snapshot.get("advertising") or {}).get("min_date") or "-")}',
        f'advertising max_date: {((snapshot.get("advertising") or {}).get("max_date") or "-")}',
        f'days covered: {int((snapshot.get("advertising") or {}).get("days_covered") or 0)}',
        f'missing days: {", ".join(((snapshot.get("advertising") or {}).get("missing_days") or [])[:15]) or "-"}',
        f'last successful update: {((snapshot.get("advertising") or {}).get("last_success") or "-")}',
        f'coverage %: {float((snapshot.get("advertising") or {}).get("coverage_percent") or 0):.1f}',
        f'status: {((snapshot.get("advertising") or {}).get("status") or "-")}',
        "",
        "FINANCE QUALITY",
        f'finance_raw_audit rows: {int((snapshot.get("finance") or {}).get("finance_raw_rows") or 0)}',
        f'expenses rows: {int((snapshot.get("finance") or {}).get("expenses_rows") or 0)}',
        f'finance min_date: {((snapshot.get("finance") or {}).get("min_date") or "-")}',
        f'finance max_date: {((snapshot.get("finance") or {}).get("max_date") or "-")}',
        f'days covered: {int((snapshot.get("finance") or {}).get("days_covered") or 0)}',
        f'missing days: {", ".join(((snapshot.get("finance") or {}).get("missing_days") or [])[:15]) or "-"}',
        f'coverage %: {float((snapshot.get("finance") or {}).get("coverage_percent") or 0):.1f}',
        f'status: {((snapshot.get("finance") or {}).get("status") or "-")}',
        "",
        "OVERALL SCORE",
        f'overall_score: {float(snapshot.get("overall_score") or 0):.1f}',
        f'overall_status: {snapshot.get("overall_status") or "-"}',
        "",
        "RECOMMENDATION",
        snapshot.get("recommendation") or "-",
    ]


def health_lines(snapshot):
    snapshot = snapshot or {}
    return [
        "SYSTEM HEALTH",
        f'bot status: {snapshot.get("bot_status") or "unknown"}',
        f'database status: {snapshot.get("database_status") or "unknown"}',
        f'database file exists: {snapshot.get("database_exists") or "unknown"}',
        f'sales rows total: {int((snapshot.get("totals") or {}).get("sales") or 0)}',
        f'orders rows total: {int((snapshot.get("totals") or {}).get("orders") or 0)}',
        f'advertising rows total: {int((snapshot.get("totals") or {}).get("advertising") or 0)}',
        f'expenses rows total: {int((snapshot.get("totals") or {}).get("expenses") or 0)}',
        f'finance_raw_audit rows total: {int((snapshot.get("totals") or {}).get("finance_raw_audit") or 0)}',
        "",
        "LAST UPDATES",
        f'sales last success: {((snapshot.get("last_updates") or {}).get("sales") or "unknown")}',
        f'orders last success: {((snapshot.get("last_updates") or {}).get("orders") or "unknown")}',
        f'advertising last success: {((snapshot.get("last_updates") or {}).get("advertising") or "unknown")}',
        f'finance last success: {((snapshot.get("last_updates") or {}).get("finance") or "unknown")}',
        "",
        "DATA FRESHNESS",
        f'sales: {((snapshot.get("freshness") or {}).get("sales") or "unknown")}',
        f'orders: {((snapshot.get("freshness") or {}).get("orders") or "unknown")}',
        f'advertising: {((snapshot.get("freshness") or {}).get("advertising") or "unknown")}',
        f'finance: {((snapshot.get("freshness") or {}).get("finance") or "unknown")}',
        "",
        "COOLDOWNS",
        f'statistics: {(((snapshot.get("cooldowns") or {}).get("statistics") or {}).get("retry_after") or "unknown")}',
        f'advertising: {(((snapshot.get("cooldowns") or {}).get("advertising") or {}).get("retry_after") or "unknown")}',
        f'finance: {(((snapshot.get("cooldowns") or {}).get("finance") or {}).get("retry_after") or "unknown")}',
        "",
        "DATA QUALITY",
        f'overall_score: {float(((snapshot.get("quality") or {}).get("overall_score") or 0)):.1f}',
        f'overall_status: {((snapshot.get("quality") or {}).get("overall_status") or "unknown")}',
        "",
        "VERDICT",
        snapshot.get("verdict") or "needs_attention",
    ]


def system_audit_lines(snapshot):
    snapshot = snapshot or {}
    health = snapshot.get("health") or {}
    quality = snapshot.get("quality") or {}
    ads_health = snapshot.get("ads_health") or {}
    finance_health = snapshot.get("finance_health") or {}
    write_safety = snapshot.get("write_safety") or {}
    cache = snapshot.get("cache") or {}
    udl_snapshot = snapshot.get("udl_snapshot") or {}
    business_metrics_snapshot = snapshot.get("business_metrics_snapshot") or {}
    financial_engine_snapshot = snapshot.get("financial_engine_snapshot") or {}
    period_snapshot = snapshot.get("period_snapshot") or {}
    sku_registry_snapshot = snapshot.get("sku_registry_snapshot") or {}
    system_audit_data_source_snapshot = snapshot.get("system_audit_data_source_snapshot") or {}
    core_v2_status = snapshot.get("core_v2_status") or {}
    core_modules = core_v2_status.get("modules") or {}
    core_commands = core_v2_status.get("commands") or {}
    lines = [
        "SYSTEM STATUS",
        "",
        "DATABASE",
        f'status: {health.get("database_status") or "unknown"}',
        "",
        "SALES",
        f'status: {((quality.get("sales") or {}).get("status") or "unknown")}',
        "",
        "ORDERS",
        f'status: {((quality.get("orders") or {}).get("status") or "unknown")}',
        "",
        "ADS",
        f'status: {ads_health.get("status") or "unknown"}',
        "",
        "FINANCE",
        f'status: {snapshot.get("finance_runtime_status") or finance_health.get("status") or "unknown"}',
        "",
        "DATA QUALITY",
        f'overall_score: {float(quality.get("overall_score") or 0):.1f}',
        f'overall_status: {quality.get("overall_status") or "unknown"}',
        f'trust_score: {snapshot.get("trust_score") if snapshot.get("trust_score") is not None else "-"}',
        "",
        "ADS HEALTH",
        f'linkability: {float(ads_health.get("linkability_percent") or 0):.1f}%',
        f'linked_spend: {money(ads_health.get("linked_spend") or 0)}',
        f'unlinked_spend: {money(ads_health.get("unlinked_spend") or 0)}',
        "",
        "Business Metrics Status",
        f'source_status: {business_metrics_snapshot.get("source_status") or "UNKNOWN"}',
        f'official_status: {business_metrics_snapshot.get("official_status") or "UNKNOWN"}',
        f'finance_api_status: {business_metrics_snapshot.get("finance_api_status") or "UNKNOWN"}',
        "",
        "UDL Status",
        f'finance source status: {(((udl_snapshot.get("sources") or {}).get("finance") or {}).get("status") or "UNKNOWN")}',
        f'payments source status: {(((udl_snapshot.get("sources") or {}).get("payments") or {}).get("status") or "UNKNOWN")}',
        f'overall trust: {((udl_snapshot.get("trust") or {}).get("overall_trust") if ((udl_snapshot.get("trust") or {}).get("overall_trust") is not None) else "-")}',
        "",
        "Financial Engine Status",
        f'status: {financial_engine_snapshot.get("status") or "UNKNOWN"}',
        f'source: {financial_engine_snapshot.get("source") or "unavailable"}',
        "",
        "Period Engine Status",
        f'type: {period_snapshot.get("period_type") or "UNKNOWN"}',
        f'display: {period_snapshot.get("display_name") or "-"}',
        "",
        "SKU Registry Coverage",
        f'coverage: {float(sku_registry_snapshot.get("coverage_percent") or 0):.1f}%',
        f'status: {sku_registry_snapshot.get("registry_status") or "UNKNOWN"}',
        "",
        "FINANCE HEALTH",
        f'real_coverage: {float(finance_health.get("real_coverage_percent") or 0):.1f}%',
        f'coverage_with_residual: {float(finance_health.get("coverage_with_residual_percent") or 0):.1f}%',
        f'wb_difference: {money(finance_health.get("wb_difference") or 0)}',
        f'residual_other_deductions: {money(finance_health.get("residual_other_deductions") or 0)}',
        "",
        "Migration Status",
        f'status: {system_audit_data_source_snapshot.get("migration_status") or "UNKNOWN"}',
        f'legacy fields: {", ".join(system_audit_data_source_snapshot.get("legacy_fallback_fields") or []) or "-"}',
        "",
        "CORE v2.0 STATUS",
        f'Financial Engine: {core_modules.get("Financial Engine") or "UNKNOWN"}',
        f'Business Metrics: {core_modules.get("Business Metrics") or "UNKNOWN"}',
        f'Unified Data Layer: {core_modules.get("Unified Data Layer") or "UNKNOWN"}',
        f'Period Engine: {core_modules.get("Period Engine") or "UNKNOWN"}',
        f'SKU Registry: {core_modules.get("SKU Registry") or "UNKNOWN"}',
        f'Dashboard: {core_commands.get("Dashboard") or "UNKNOWN"}',
        f'CEO Report: {core_commands.get("CEO Report") or "UNKNOWN"}',
        f'Money Flow: {core_commands.get("Money Flow") or "UNKNOWN"}',
        f'Profit Audit: {core_commands.get("Profit Audit") or "UNKNOWN"}',
        f'Advisor: {core_commands.get("Advisor") or "UNKNOWN"}',
        f'AI Director: {core_commands.get("AI Director") or "UNKNOWN"}',
        f'Control Center: {core_commands.get("Control Center") or "UNKNOWN"}',
        f'Product readiness: {core_commands.get("Product Readiness") or "UNKNOWN"}',
        f'Project structure readiness: {core_commands.get("Project Structure Readiness") or "UNKNOWN"}',
        f'System Audit: {core_commands.get("System Audit") or "UNKNOWN"}',
        "",
        "CACHE",
        f'sales cache: atomic={((cache.get("sales") or {}).get("atomic_write") or "no")} | readback={((cache.get("sales") or {}).get("readback_validation") or "no")} | cleanup={((cache.get("sales") or {}).get("mismatch_cleanup") or "no")}',
        f'ads cache: atomic={((cache.get("ads") or {}).get("atomic_write") or "no")} | readback={((cache.get("ads") or {}).get("readback_validation") or "no")} | cleanup={((cache.get("ads") or {}).get("mismatch_cleanup") or "no")}',
        "",
        "COOLDOWNS",
        f'ads: {(((snapshot.get("cooldowns") or {}).get("advertising") or {}).get("retry_after") or "unknown")}',
        f'statistics: {(((snapshot.get("cooldowns") or {}).get("statistics") or {}).get("retry_after") or "unknown")}',
        "",
        "LAST SUCCESSFUL UPDATE",
        f'sales: {((snapshot.get("last_updates") or {}).get("sales") or "unknown")}',
        f'ads: {((snapshot.get("last_updates") or {}).get("advertising") or "unknown")}',
        f'finance: {((snapshot.get("last_updates") or {}).get("finance") or "unknown")}',
        "",
        "WRITE SAFETY",
    ]
    for command_name in ("sales applyhistorical", "ads applyhistorical", "ads cleanuphistorical"):
        row = write_safety.get(command_name) or {}
        lines.append(
            f'{command_name}: guard={row.get("guard") or "no"} | '
            f'db_before={row.get("db_before") or "no"} | '
            f'db_after={row.get("db_after") or "no"} | '
            f'cache_validation={row.get("cache_validation") or "no"} | '
            f'cooldown_safe={row.get("cooldown_safe") or "no"} | '
            f'rollback={row.get("rollback") or "no"}'
        )
    lines.extend(["", *finance_debug_lines(finance_health), "", "VERDICT", snapshot.get("verdict") or "needs_attention"])
    return lines
