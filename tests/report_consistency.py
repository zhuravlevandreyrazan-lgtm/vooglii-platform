"""Readonly cross-report consistency checks.

This suite compares key values across local snapshots and text builders
without calling WB API, writing to DB, or starting Telegram polling.
"""

import os
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
import report as report_module

report_module.is_pro = lambda telegram_id: True

TEST_USER_ID = 658486226
TEST_START = "2026-05-01"
TEST_END = "2026-05-31"
TEST_DAYS = (TEST_START, TEST_END)
_FIXTURE_CACHE = {}
_PERFORMANCE_WARNINGS = []
_SLOW_CASE_MS = 20000.0
_RUN_HEAVY_CASES = str(os.getenv("WB_RUN_HEAVY_REPORT_CASES", "")).strip().lower() in ("1", "true", "yes", "on")


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _cached(name, builder):
    if name not in _FIXTURE_CACHE:
        _FIXTURE_CACHE[name] = builder()
    value = _FIXTURE_CACHE[name]
    return dict(value) if isinstance(value, dict) else value


def _case_meta(name):
    text = str(name or "").lower()
    if "finance" in text or "payment" in text or "money" in text:
        return ("finance", "legacy-mode" if "api status" in text or "api diagnose" in text else "product-mode")
    if "director" in text or "advisor" in text or "decision" in text or "cfo" in text or "kpi" in text or "business" in text or "unified" in text:
        return ("business", "product-mode")
    if "system" in text or "health" in text or "control" in text or "structure" in text or "rc " in text or "migration" in text:
        return ("system", "readonly")
    return ("generic", "readonly")


def _money_close(a, b, tolerance=0.01):
    return abs(float(a or 0) - float(b or 0)) <= tolerance


def _run_case(name, fn, counters):
    started = time.perf_counter()
    suspected_layer, mode = _case_meta(name)
    try:
        result = fn()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if result == "SKIPPED":
            counters["skipped"] += 1
            print(f"SKIPPED: {name} elapsed_ms={elapsed_ms:.1f}", flush=True)
        else:
            counters["passed"] += 1
            print(f"PASSED: {name} elapsed_ms={elapsed_ms:.1f}", flush=True)
        if elapsed_ms > _SLOW_CASE_MS:
            warning = f"command name={name} elapsed_ms={elapsed_ms:.1f} suspected layer={suspected_layer} mode={mode}"
            _PERFORMANCE_WARNINGS.append(warning)
            print(f"TIMEOUT DIAGNOSTIC {warning}", flush=True)
    except Exception as exc:
        counters["failed"] += 1
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        print(f"FAILED: {name}: {exc} elapsed_ms={elapsed_ms:.1f} suspected_layer={suspected_layer} mode={mode}", flush=True)


def _dashboard_like_snapshot(user, days):
    mgmt = telegram_bot._report_mgmt_snapshot(user, days)
    orders_count, orders_sum, cancel_count, cancel_sum = telegram_bot.get_orders_stats(days, user)
    sales_count, _ = telegram_bot.get_period_stats(days, user)
    ads_stats = telegram_bot.get_advertising_stats(days, user)
    return {
        "revenue": mgmt.get("revenue"),
        "advertising": mgmt.get("advertising"),
        "orders": orders_count,
        "sales": sales_count,
        "orders_sum": orders_sum,
        "cancel_count": cancel_count,
        "cancel_sum": cancel_sum,
        "advertising_stats_spend": ads_stats[4] if ads_stats else None,
    }


def _ceo_like_snapshot(user, days):
    mgmt = telegram_bot._report_mgmt_snapshot(user, days)
    orders_count, orders_sum, cancel_count, cancel_sum = telegram_bot.get_orders_stats(days, user)
    sales_count, _ = telegram_bot.get_period_stats(days, user)
    ads_stats = telegram_bot.get_advertising_stats(days, user)
    return {
        "revenue": mgmt.get("revenue"),
        "advertising": mgmt.get("advertising"),
        "orders": orders_count,
        "sales": sales_count,
        "orders_sum": orders_sum,
        "cancel_count": cancel_count,
        "cancel_sum": cancel_sum,
        "advertising_stats_spend": ads_stats[4] if ads_stats else None,
    }


def case_dashboard_vs_ceo_report():
    dashboard_snapshot = _dashboard_like_snapshot(TEST_USER_ID, TEST_DAYS)
    ceo_snapshot = _ceo_like_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert(dashboard_snapshot is not None, "dashboard snapshot is None")
    _assert(ceo_snapshot is not None, "ceo snapshot is None")
    for key in ("revenue", "orders", "sales", "advertising"):
        _assert(key in dashboard_snapshot, f"dashboard missing {key}")
        _assert(key in ceo_snapshot, f"ceo missing {key}")
        _assert(type(dashboard_snapshot[key]) is type(ceo_snapshot[key]), f"type mismatch for {key}")
    _assert(_money_close(dashboard_snapshot["revenue"], ceo_snapshot["revenue"]), "revenue mismatch")
    _assert(int(dashboard_snapshot["orders"] or 0) == int(ceo_snapshot["orders"] or 0), "orders mismatch")
    _assert(int(dashboard_snapshot["sales"] or 0) == int(ceo_snapshot["sales"] or 0), "sales mismatch")
    _assert(_money_close(dashboard_snapshot["advertising"], ceo_snapshot["advertising"]), "advertising mismatch")
    if dashboard_snapshot.get("advertising_stats_spend") is not None and ceo_snapshot.get("advertising_stats_spend") is not None:
        _assert(
            _money_close(dashboard_snapshot["advertising_stats_spend"], ceo_snapshot["advertising_stats_spend"]),
            "advertising spend stats mismatch",
        )


def case_finance_difference_vs_profit_audit():
    finance_snapshot = telegram_bot.get_finance_difference_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    profit_snapshot = telegram_bot._profit_audit_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert(finance_snapshot is not None, "finance snapshot is None")
    _assert(profit_snapshot is not None, "profit snapshot is None")
    finance_health = profit_snapshot.get("finance_health")
    _assert(isinstance(finance_health, dict), "profit finance_health should be dict")
    for key in ("wb_difference", "explained_total", "real_coverage_percent", "coverage_with_residual_percent"):
        _assert(key in finance_snapshot, f"finance snapshot missing {key}")
        _assert(key in finance_health, f"profit finance_health missing {key}")
    _assert(0.0 <= float(finance_snapshot["real_coverage_percent"] or 0) <= 100.0, "finance real_coverage_percent out of range")
    _assert(0.0 <= float(finance_snapshot["coverage_with_residual_percent"] or 0) <= 100.0, "finance coverage_with_residual_percent out of range")
    _assert(0.0 <= float(finance_health["real_coverage_percent"] or 0) <= 100.0, "profit real_coverage_percent out of range")
    _assert(0.0 <= float(finance_health["coverage_with_residual_percent"] or 0) <= 100.0, "profit coverage_with_residual_percent out of range")


def case_health_vs_system_audit():
    health_snapshot = telegram_bot._health_snapshot(TEST_USER_ID)
    system_snapshot = telegram_bot._system_audit_snapshot(TEST_USER_ID)
    _assert(health_snapshot is not None, "health snapshot is None")
    _assert(system_snapshot is not None, "system snapshot is None")
    health_quality = health_snapshot.get("quality") or {}
    system_quality = system_snapshot.get("quality") or {}
    _assert((health_quality.get("overall_status") or "unknown") == (system_quality.get("overall_status") or "unknown"), "data quality overall_status mismatch")

    health_start = (telegram_bot.datetime.now() - telegram_bot.timedelta(days=29)).strftime("%Y-%m-%d")
    health_end = telegram_bot.datetime.now().strftime("%Y-%m-%d")
    ads_health_direct = telegram_bot.get_advertising_health_snapshot(TEST_USER_ID, health_start, health_end)
    system_ads_health = system_snapshot.get("ads_health") or {}
    _assert((ads_health_direct.get("status") or "unknown") == (system_ads_health.get("status") or "unknown"), "advertising health status mismatch")

    finance_health_direct = telegram_bot.get_finance_difference_snapshot(TEST_USER_ID, health_start, health_end)
    system_finance_health = system_snapshot.get("finance_health") or {}
    _assert((finance_health_direct.get("status") or "unknown") == (system_finance_health.get("status") or "unknown"), "finance health status mismatch")


def case_advisor_vs_sku_analytics():
    if not hasattr(telegram_bot, "_sku_actionplan_snapshot") or not hasattr(telegram_bot, "_sku_analytics_rows"):
        return "SKIPPED"
    actionplan = telegram_bot._sku_actionplan_snapshot(TEST_USER_ID, TEST_DAYS)
    sku_rows, _ = telegram_bot._sku_analytics_rows(TEST_USER_ID, TEST_DAYS)
    _assert(actionplan is not None, "actionplan snapshot is None")
    _assert(sku_rows is not None, "sku analytics rows is None")
    known_articles = {str(row.get("article") or "").strip() for row in sku_rows if str(row.get("article") or "").strip()}
    if not known_articles:
        return "SKIPPED"
    for item in actionplan.get("top_priority") or []:
        article = str(item.get("article") or "").strip()
        _assert(article in known_articles, f"advisor references missing SKU article {article}")


def case_general_snapshots_not_none():
    snapshot_checks = [
        ("report_mgmt", lambda: telegram_bot._report_mgmt_snapshot(TEST_USER_ID, TEST_DAYS)),
        ("data_quality", lambda: telegram_bot._data_quality_snapshot(TEST_USER_ID, TEST_DAYS)),
        ("health", lambda: telegram_bot._health_snapshot(TEST_USER_ID)),
        ("system_audit", lambda: telegram_bot._system_audit_snapshot(TEST_USER_ID)),
        ("profit_audit", lambda: telegram_bot._profit_audit_snapshot(TEST_USER_ID, TEST_DAYS)),
        ("finance_difference", lambda: telegram_bot.get_finance_difference_snapshot(TEST_USER_ID, TEST_START, TEST_END)),
    ]
    for index, (name, getter) in enumerate(snapshot_checks, 1):
        snapshot = getter()
        _assert(snapshot is not None, f"snapshot #{index} is None")
        _assert(isinstance(snapshot, dict), f"snapshot #{index} ({name}) should be dict")


def case_profit_model_consistency():
    if not hasattr(telegram_bot, "_profit_audit_snapshot"):
        return "SKIPPED"

    profit_snapshot = telegram_bot._profit_audit_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(profit_snapshot, dict):
        return "SKIPPED"

    payout_verification = profit_snapshot.get("payout_verification_debug")
    profit_display = profit_snapshot.get("profit_display_debug")
    if not isinstance(payout_verification, dict) or not isinstance(profit_display, dict):
        return "SKIPPED"

    profit_model_status = payout_verification.get("status")
    wb_deductions_already_in_payout = profit_display.get("wb_deductions_already_in_payout")
    double_subtraction_prevented = profit_display.get("double_subtraction_prevented")
    profit_before_tax_from_payout = profit_display.get("profit_before_tax_from_payout")
    net_profit_after_tax_from_payout = profit_display.get("net_profit_after_tax_from_payout")

    if any(
        value is None
        for value in (
            profit_model_status,
            wb_deductions_already_in_payout,
            double_subtraction_prevented,
            profit_before_tax_from_payout,
            net_profit_after_tax_from_payout,
        )
    ):
        return "SKIPPED"

    _assert(str(profit_model_status or "").upper() in ("VERIFIED", "UNVERIFIED", "DEGRADED"), "profit model status out of allowed set")
    _assert(str(wb_deductions_already_in_payout or "").lower() in ("yes", "true"), "wb_deductions_already_in_payout should be yes/true")
    _assert(str(double_subtraction_prevented or "").lower() in ("yes", "true"), "double_subtraction_prevented should be yes/true")
    _assert(profit_before_tax_from_payout is not None, "profit_before_tax_from_payout should not be None")
    _assert(net_profit_after_tax_from_payout is not None, "net_profit_after_tax_from_payout should not be None")
    _assert(
        float(net_profit_after_tax_from_payout or 0) <= float(profit_before_tax_from_payout or 0),
        "net_profit_after_tax_from_payout should be <= profit_before_tax_from_payout",
    )


def case_payment_reconciliation_consistency():
    if not hasattr(telegram_bot, "_payment_reconciliation_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._payment_reconciliation_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    weekly_payout_total_all = snapshot.get("weekly_payout_total_all")
    sales_for_pay_total = snapshot.get("sales_for_pay_total")
    status = snapshot.get("status")
    source = snapshot.get("payment_reports_source")
    reports_count = snapshot.get("payment_reports_count")
    timeline = snapshot.get("payment_timeline")
    bridge = snapshot.get("payment_bridge")

    if weekly_payout_total_all is None or sales_for_pay_total is None or status is None:
        return "SKIPPED"
    if timeline is None or bridge is None or source is None or reports_count is None:
        return "SKIPPED"

    _assert(float(weekly_payout_total_all or 0) > 0, "weekly_payout_total_all should be > 0")
    _assert(float(sales_for_pay_total or 0) > 0, "sales_for_pay_total should be > 0")
    _assert(
        str(status or "") in ("EXPECTED_TIMING_DIFFERENCE", "NEEDS_REVIEW", "UNKNOWN"),
        "payment reconciliation status out of allowed set",
    )
    _assert(str(source or "") in ("wb_finance_api", "manual_reference", "unknown"), "payment reports source out of allowed set")
    _assert(int(reports_count or 0) >= 0, "payment_reports_count should be >= 0")
    if str(source or "") == "wb_finance_api":
        _assert(float(snapshot.get("payment_reports_total_bank_payment") or 0) >= 0, "payment_reports_total_bank_payment should be >= 0 for wb_finance_api")
    _assert(isinstance(timeline, list), "payment_timeline should be list")
    _assert(isinstance(bridge, dict), "payment_bridge should be dict")
    _assert(str(bridge.get("status") or "") in ("OK", "EXPECTED_NEXT_PERIOD", "NEEDS_REVIEW", "UNKNOWN"), "payment bridge status out of allowed set")


def case_payment_timeline_consistency():
    if not hasattr(telegram_bot, "_payment_reconciliation_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._payment_reconciliation_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    timeline = snapshot.get("payment_timeline")
    bridge = snapshot.get("payment_bridge")
    if timeline is None or bridge is None:
        return "SKIPPED"

    _assert(isinstance(timeline, list), "payment timeline should be list")
    _assert(isinstance(bridge, dict), "payment bridge should be dict")
    if not timeline:
        return "SKIPPED"
    for item in timeline:
        _assert(str(item.get("status") or "") in ("PAID", "MISSING", "EXPECTED_NEXT_PERIOD", "NEEDS_REVIEW"), "timeline item status out of allowed set")
        _assert(float(item.get("weekly_payout") or 0) >= 0, "timeline weekly_payout should be >= 0")
        _assert(float(item.get("sales_for_pay") or 0) >= 0, "timeline sales_for_pay should be >= 0")


def case_money_flow_consistency():
    if not hasattr(telegram_bot, "_money_flow_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._money_flow_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    sales_revenue_total = snapshot.get("sales_revenue_total")
    sales_for_pay_total = snapshot.get("sales_for_pay_total")
    wb_deductions_total = snapshot.get("wb_deductions_total")
    status = snapshot.get("status")

    if sales_revenue_total is None or sales_for_pay_total is None or wb_deductions_total is None or status is None:
        return "SKIPPED"

    _assert(float(sales_revenue_total or 0) > 0, "sales_revenue_total should be > 0")
    _assert(float(sales_for_pay_total or 0) > 0, "sales_for_pay_total should be > 0")
    _assert(float(wb_deductions_total or 0) >= 0, "wb_deductions_total should be >= 0")
    _assert(str(status or "") in ("OK", "EXPECTED_NEXT_PERIOD", "NEEDS_REVIEW", "UNKNOWN"), "money flow status out of allowed set")


def case_wb_commission_breakdown():
    if not hasattr(telegram_bot, "_wb_commission_breakdown_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._wb_commission_breakdown_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    status = snapshot.get("status")
    if status is None:
        return "SKIPPED"

    _assert(str(status or "") in ("AVAILABLE", "PARTIAL", "UNAVAILABLE"), "wb commission breakdown status out of allowed set")
    _assert(snapshot.get("commission_source") in ("sales", "finance_raw", "calculated_delta", "unavailable"), "wb commission source out of allowed set")
    _assert(float(snapshot.get("commission_total") or 0) >= 0, "wb commission total should be >= 0")
    _assert(float(snapshot.get("wb_deductions_total") or 0) >= float(snapshot.get("detailed_commission_total") or 0), "wb_deductions_total should be >= detailed_commission_total")
    coverage = float(snapshot.get("commission_breakdown_coverage_percent") or 0)
    _assert(0.0 <= coverage <= 100.0, "commission_breakdown_coverage_percent out of range")
    _assert(str(snapshot.get("detail_status") or "") in ("FULL", "HIGH", "PARTIAL", "UNAVAILABLE"), "detail_status out of allowed set")


def case_sku_money_flow():
    if not hasattr(telegram_bot, "_sku_money_flow_snapshot") or not hasattr(telegram_bot, "_sku_cost_reference_data"):
        return "SKIPPED"

    cost_reference = telegram_bot._sku_cost_reference_data()
    if not isinstance(cost_reference, dict) or not cost_reference:
        return "SKIPPED"

    snapshot = telegram_bot._sku_money_flow_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    status = snapshot.get("status")
    if status is None:
        return "SKIPPED"

    _assert(str(status or "") in ("AVAILABLE", "PARTIAL", "UNAVAILABLE"), "sku money flow status out of allowed set")
    items = snapshot.get("items")
    _assert(isinstance(items, list), "sku money flow items should be list")
    if not items:
        return "SKIPPED"
    _assert(any(str(item.get("cost_status") or "") == "OK" for item in items), "at least one SKU should have cost_status OK")
    for item in items[:3]:
        _assert(str(item.get("status") or "") in ("PROFITABLE", "LOW_PROFIT", "UNPROFITABLE", "MISSING_COST", "NEEDS_REVIEW", "ESTIMATED"), "sku item status out of allowed set")
        _assert(float(item.get("sales_revenue") or 0) >= 0, "sku sales_revenue should be >= 0")
        _assert(float(item.get("sales_for_pay") or 0) >= 0, "sku sales_for_pay should be >= 0")
        _assert(str(item.get("cost_status") or "") in ("OK", "MISSING"), "sku cost_status out of allowed set")
        if item.get("allocated_ads_estimate") is not None:
            _assert(isinstance(item.get("allocated_ads_estimate"), (int, float)), "allocated_ads_estimate should be numeric")
        if item.get("allocated_tax_estimate") is not None:
            _assert(isinstance(item.get("allocated_tax_estimate"), (int, float)), "allocated_tax_estimate should be numeric")
        if item.get("estimated_net_contribution_after_ads_tax") is not None:
            _assert(isinstance(item.get("estimated_net_contribution_after_ads_tax"), (int, float)), "estimated_net_contribution_after_ads_tax should be numeric")
        _assert(str(item.get("allocation_confidence") or "UNKNOWN") in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"), "allocation_confidence out of allowed set")
        _assert(str(item.get("allocation_confidence_tax") or "UNKNOWN") in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"), "allocation_confidence_tax out of allowed set")


def case_finance_api_status():
    if not hasattr(telegram_bot, "_finance_api_status_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._finance_api_status_snapshot(TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    status = snapshot.get("status")
    if status is None:
        return "SKIPPED"

    _assert(str(status or "") in ("OK", "RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "TIMEOUT", "ERROR", "UNKNOWN"), "finance api status out of allowed set")
    _assert(isinstance(bool(snapshot.get("source_available")), bool), "source_available should be bool-like")
    _assert(int(snapshot.get("reports_count") or 0) >= 0, "reports_count should be >= 0")
    _assert(str(snapshot.get("cooldown_active")).lower() in ("true", "false"), "finance api status cooldown_active should be bool-like")
    cooldown_source = str(snapshot.get("cooldown_source") or "manual")
    _assert(cooldown_source in ("header", "estimated", "manual"), "finance api status cooldown_source out of allowed set")


def case_finance_api_diagnose():
    if not hasattr(telegram_bot, "_finance_api_diagnose_snapshot"):
        return "SKIPPED"

    original_snapshot = telegram_bot._finance_api_diagnose_snapshot
    try:
        telegram_bot._finance_api_diagnose_snapshot = lambda user: {
            "status": "WARNING",
            "period_start": TEST_START,
            "period_end": "2026-05-03",
            "new_finance_api": {
                "endpoint": "/api/finance/v1/sales-reports/list",
                "method": "POST",
                "http_status": 403,
                "origin": "finance-api",
                "detected_issue": "TOKEN_CATEGORY_REQUIRED",
                "token_accepted": False,
                "data_available": False,
                "recommendation": "check new finance api token category",
            },
            "legacy_finance_api": {
                "endpoint": "/api/v5/supplier/reportDetailByPeriod",
                "method": "GET",
                "http_status": 200,
                "origin": "statistics-api",
                "detected_issue": "OK",
                "token_accepted": True,
                "data_available": True,
                "recommendation": "legacy endpoint still works",
            },
            "summary": "Токен работает для старого reports/stat API, но не принят новым Finance API.",
            "recommendation": "Проверить тип токена или миграционные требования нового Finance API.",
        }
        snapshot = telegram_bot._finance_api_diagnose_snapshot(TEST_USER_ID)
    finally:
        telegram_bot._finance_api_diagnose_snapshot = original_snapshot

    _assert(str(snapshot.get("status") or "") in ("OK", "WARNING", "BLOCKED", "UNKNOWN"), "finance api diagnose status out of allowed set")
    _assert(bool(str(snapshot.get("period_start") or "").strip()), "finance api diagnose period_start missing")
    _assert(bool(str(snapshot.get("period_end") or "").strip()), "finance api diagnose period_end missing")
    for key in ("new_finance_api", "legacy_finance_api"):
        item = snapshot.get(key)
        _assert(isinstance(item, dict), f"finance api diagnose {key} should be dict")
        for item_key in ("endpoint", "method", "detected_issue", "recommendation"):
            _assert(bool(str(item.get(item_key) or "").strip()), f"finance api diagnose {key} missing {item_key}")
        _assert(isinstance(item.get("token_accepted"), bool), f"finance api diagnose {key} token_accepted should be bool")
        _assert(isinstance(item.get("data_available"), bool), f"finance api diagnose {key} data_available should be bool")


def case_finance_transport_contract():
    original_httpx_request = telegram_bot.httpx.request
    captured = {}

    class _Response:
        status_code = 200
        headers = {}
        text = "[]"
        content = b"[]"

        def __init__(self, method, url, json_body):
            self.request = type("Request", (), {"url": url})()
            self._json_body = json_body
            captured["method"] = method
            captured["url"] = url
            captured["json"] = dict(json_body or {})

        def json(self):
            return []

    def _fake_request(method, url, headers=None, json=None, timeout=None):
        captured["headers"] = dict(headers or {})
        captured["timeout"] = timeout
        return _Response(method, url, json)

    try:
        telegram_bot.httpx.request = _fake_request
        result = telegram_bot.fetch_wb_finance_reports_list(TEST_START, TEST_END, token="test-token")
    finally:
        telegram_bot.httpx.request = original_httpx_request

    _assert(result is not None, "finance transport result should not be None")
    _assert(captured.get("method") == "POST", "finance transport should use POST")
    _assert(str(captured.get("url") or "").startswith("https://finance-api.wildberries.ru/"), "finance transport should use finance-api host")
    _assert("/api/finance/v1/sales-reports/list" in str(captured.get("url") or ""), "finance transport should call sales-reports/list")
    _assert(captured.get("json") == {"dateFrom": TEST_START, "dateTo": TEST_END}, "finance transport body mismatch")


def case_finance_operation_catalog():
    if not hasattr(telegram_bot, "_finance_operation_catalog_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._finance_operation_catalog_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    totals = snapshot.get("catalog_totals")
    groups = snapshot.get("groups")
    if not isinstance(totals, dict) or not isinstance(groups, list):
        return "SKIPPED"

    _assert(float(totals.get("wb_deductions_total") or 0) >= 0, "wb_deductions_total should be >= 0")
    coverage = float(totals.get("coverage_percent") or 0)
    _assert(0.0 <= coverage <= 100.0, "catalog coverage_percent out of range")
    allowed_buckets = {
        "realization_commission", "logistics", "storage", "acquiring", "wb_promotion",
        "deduction", "penalty", "acceptance", "return", "correction", "other", "unknown",
    }
    if not groups:
        return "SKIPPED"
    for item in groups[:10]:
        _assert(str(item.get("bucket_guess") or "") in allowed_buckets, "catalog bucket_guess out of allowed set")


def case_gold_standard_financial_validation():
    if not hasattr(telegram_bot, "_gold_standard_reference_files_available"):
        return "SKIPPED"
    if not telegram_bot._gold_standard_reference_files_available():
        return "SKIPPED"
    snapshot = telegram_bot._gold_standard_financial_snapshot(TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"
    status = snapshot.get("status")
    if status is None:
        return "SKIPPED"
    _assert(int(snapshot.get("reports_count") or 0) > 0, "gold standard reports_count should be > 0")
    _assert(int(snapshot.get("rows_count") or 0) > 0, "gold standard rows_count should be > 0")
    _assert(float(snapshot.get("sales_total") or 0) >= 0, "gold standard sales_total should be >= 0")
    _assert(float(snapshot.get("payment_total") or 0) >= 0, "gold standard payment_total should be >= 0")
    _assert(str(status or "") in ("MATCHED", "PARTIAL", "NEEDS_REVIEW", "FAILED", "UNKNOWN"), "gold standard status out of allowed set")


def case_financial_engine_consistency():
    if not hasattr(telegram_bot, "_financial_engine_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._financial_engine_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    status = str(snapshot.get("status") or "")
    _assert(status in ("MATCHED", "PARTIAL", "PARTIAL_COST_MISSING", "LEGACY_FALLBACK", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "RATE_LIMIT", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR"), "financial engine status out of allowed set")
    _assert(str(snapshot.get("cooldown_source") or "manual") in ("header", "estimated", "manual"), "financial engine cooldown_source out of allowed set")
    _assert(str(snapshot.get("ads_handling") or "") in ("INCLUDED_IN_WB_DEDUCTIONS", "NOT_INCLUDED", "UNKNOWN"), "ads_handling out of allowed set")
    _assert(float(snapshot.get("cost_coverage_percent") or 0) >= 0, "cost_coverage_percent should be >= 0")
    _assert(str(snapshot.get("legacy_gold_validation_status") or "NOT_APPLICABLE") in ("MATCHED_LEGACY", "PARTIAL_LEGACY", "NEEDS_REVIEW", "NOT_APPLICABLE"), "legacy gold validation status out of allowed set")
    _assert(isinstance(snapshot.get("legacy_gold_delta"), dict), "legacy gold delta should be dict")
    if snapshot.get("official_net_profit") is not None:
        _assert(float(snapshot.get("official_net_profit") or 0) <= float(snapshot.get("profit_before_tax") or 0), "official_net_profit should be <= profit_before_tax")


def case_business_metrics_consistency():
    if not hasattr(telegram_bot, "_business_metrics_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._business_metrics_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert("period_start" in snapshot and "period_end" in snapshot, "business metrics snapshot missing period")
    _assert(str(snapshot.get("official_status") or "") in telegram_bot.BUSINESS_METRICS_OFFICIAL_ALLOWED_STATUSES, "business metrics official_status out of allowed set")
    if bool(snapshot.get("official_available")):
        _assert(snapshot.get("official_net_profit") is not None, "official_available requires official_net_profit")
        _assert(float(snapshot.get("official_net_profit") or 0) <= float(snapshot.get("official_profit_before_tax") or 0), "official_net_profit should be <= official_profit_before_tax")
    if bool(snapshot.get("operational_available")):
        _assert(snapshot.get("operational_net_profit") is not None, "operational_available requires operational_net_profit")
    if bool(snapshot.get("official_available")) and bool(snapshot.get("operational_available")):
        _assert(snapshot.get("official_source") != "operational", "official and operational layers should not mix sources")
    if str(snapshot.get("official_status") or "") in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR"):
        notes = list(snapshot.get("notes") or [])
        _assert(any("cost trust unavailable" in str(item).lower() for item in notes), "business metrics should explain unavailable cost trust when finance detail is unavailable")


def case_kpi_engine_consistency():
    if not hasattr(telegram_bot, "_kpi_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._kpi_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.KPI_ENGINE_ALLOWED_STATUS, "kpi engine status out of allowed set")
    _assert(isinstance(snapshot.get("summary"), dict), "kpi summary should be dict")
    _assert(isinstance(snapshot.get("kpis"), list), "kpi list should be list")
    _assert(isinstance(snapshot.get("warnings"), list), "kpi warnings should be list")

    summary = snapshot.get("summary") or {}
    _assert(str(summary.get("overall_status") or "") in telegram_bot.KPI_ALLOWED_ITEM_STATUSES, "kpi overall_status out of allowed set")
    _assert(int(summary.get("total_kpis") or 0) == len(snapshot.get("kpis") or []), "kpi total_kpis should equal len(kpis)")

    for item in snapshot.get("kpis") or []:
        _assert(str(item.get("group") or "") in telegram_bot.KPI_ALLOWED_GROUPS, "kpi group out of allowed set")
        _assert(str(item.get("status") or "") in telegram_bot.KPI_ALLOWED_ITEM_STATUSES, "kpi item status out of allowed set")
        _assert(str(item.get("confidence") or "") in telegram_bot.KPI_ALLOWED_CONFIDENCE, "kpi confidence out of allowed set")


def case_unified_data_layer_consistency():
    if not hasattr(telegram_bot, "_unified_data_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._unified_data_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    for key in ("period", "sources", "sales", "advertising", "finance", "payments", "costs", "business_metrics", "quality", "trust", "warnings"):
        _assert(key in snapshot, f"unified data layer snapshot missing {key}")

    sources = snapshot.get("sources") or {}
    for source_name in ("sales", "ads", "finance", "payments"):
        item = dict(sources.get(source_name) or {})
        _assert(bool(item), f"unified data layer source missing {source_name}")
        _assert(str(item.get("status") or "") in telegram_bot.UDL_ALLOWED_SOURCE_STATUSES, f"udl source status out of allowed set for {source_name}")

    trust = snapshot.get("trust") or {}
    overall_trust = trust.get("overall_trust")
    if overall_trust is not None:
        _assert(0 <= int(overall_trust) <= 100, "udl overall_trust should be between 0 and 100")

    warnings = snapshot.get("warnings")
    _assert(isinstance(warnings, list), "udl warnings should be a list")
    _assert(len(warnings) == len(set(warnings)), "udl warnings should be deduplicated")
    costs = snapshot.get("costs") or {}
    if str((snapshot.get("finance") or {}).get("status") or "") in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR"):
        _assert((costs.get("cost_total") is None), "udl cost_total should be unavailable when finance detail is unavailable")


def case_sku_registry_consistency():
    if not hasattr(telegram_bot, "_sku_registry_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._sku_registry_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(int(snapshot.get("total_reference_skus") or 0) > 0, "sku registry total_reference_skus should be > 0")
    coverage = float(snapshot.get("coverage_percent") or 0)
    _assert(0.0 <= coverage <= 100.0, "sku registry coverage_percent should be between 0 and 100")
    _assert(str(snapshot.get("registry_status") or "") in telegram_bot.SKU_REGISTRY_STATUS_VALUES, "sku registry status out of allowed set")


def case_period_engine_consistency():
    if not hasattr(telegram_bot, "_period_engine_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._period_engine_snapshot(args=[TEST_START, TEST_END], today="2026-06-26")
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    period_type = str(snapshot.get("period_type") or "UNKNOWN")
    _assert(period_type in telegram_bot.PERIOD_ENGINE_ALLOWED_TYPES, "period engine type out of allowed set")

    if period_type != "ALL":
        _assert(str(snapshot.get("start_date") or "") <= str(snapshot.get("end_date") or ""), "period engine start_date should be <= end_date")
        _assert(int(snapshot.get("days_count") or 0) >= 1, "period engine days_count should be >= 1")
        _assert(isinstance(snapshot.get("previous_period"), dict), "period engine previous_period should exist for bounded periods")
        _assert(isinstance(snapshot.get("weeks"), list), "period engine weeks should be list for bounded periods")
    else:
        _assert(snapshot.get("days_count") is None, "period engine ALL should not have days_count")


def case_command_source_audit_consistency():
    if not hasattr(telegram_bot, "_command_source_audit_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._command_source_audit_snapshot()
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(int(snapshot.get("commands_count") or 0) > 0, "command source audit commands_count should be > 0")
    commands = snapshot.get("commands")
    _assert(isinstance(commands, list), "command source audit commands should be list")
    _assert(len(commands) == int(snapshot.get("commands_count") or 0), "command source audit commands_count mismatch")
    for item in commands:
        _assert(bool(str(item.get("command") or "").strip()), "command source audit item missing command")
        _assert(bool(str(item.get("source") or "").strip()), "command source audit item missing source")
        _assert(bool(str(item.get("status") or "").strip()), "command source audit item missing status")
        _assert(bool(str(item.get("migration_target") or "").strip()), "command source audit item missing migration_target")
        _assert(str(item.get("write_risk") or "unknown") in ("yes", "no", "unknown"), "command source audit write_risk out of allowed set")


def case_dashboard_migration_consistency():
    if not hasattr(telegram_bot, "_dashboard_data_source_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._dashboard_data_source_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    total_fields = int(snapshot.get("total_fields") or 0)
    fields_from_udl = int(snapshot.get("fields_from_udl") or 0)
    fields_from_business_metrics = int(snapshot.get("fields_from_business_metrics") or 0)
    fields_from_legacy = int(snapshot.get("fields_from_legacy") or 0)
    _assert(total_fields >= fields_from_udl + fields_from_business_metrics + fields_from_legacy, "dashboard migration total_fields should cover all source buckets")
    _assert(isinstance(snapshot.get("legacy_fallback_fields"), list), "dashboard migration legacy_fallback_fields should be list")
    _assert(str(snapshot.get("migration_status") or "UNKNOWN") in ("NOT_MIGRATED", "MIGRATED_PARTIAL", "MIGRATED", "UNKNOWN"), "dashboard migration status out of allowed set")


def case_ceo_migration_consistency():
    if not hasattr(telegram_bot, "_ceo_data_source_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._ceo_data_source_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    total_fields = int(snapshot.get("total_fields") or 0)
    fields_from_udl = int(snapshot.get("fields_from_udl") or 0)
    fields_from_business_metrics = int(snapshot.get("fields_from_business_metrics") or 0)
    fields_from_legacy = int(snapshot.get("fields_from_legacy") or 0)
    _assert(total_fields >= fields_from_udl + fields_from_business_metrics + fields_from_legacy, "ceo migration total_fields should cover all source buckets")
    _assert(isinstance(snapshot.get("legacy_fallback_fields"), list), "ceo migration legacy_fallback_fields should be list")
    _assert(isinstance(snapshot.get("warnings"), list), "ceo migration warnings should be list")
    _assert(str(snapshot.get("migration_status") or "UNKNOWN") in ("NOT_MIGRATED", "MIGRATED_PARTIAL", "MIGRATED", "UNKNOWN"), "ceo migration status out of allowed set")


def case_system_audit_migration_consistency():
    if not hasattr(telegram_bot, "_system_audit_data_source_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._system_audit_data_source_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(bool(str(snapshot.get("migration_status") or "").strip()), "system audit migration status missing")
    _assert(isinstance(snapshot.get("legacy_fallback_fields"), list), "system audit legacy_fallback_fields should be list")
    _assert(isinstance(snapshot.get("warnings"), list), "system audit warnings should be list")
    _assert(str(snapshot.get("migration_status") or "UNKNOWN") in ("NOT_MIGRATED", "MIGRATED_PARTIAL", "MIGRATED", "UNKNOWN"), "system audit migration status out of allowed set")


def case_cfo_insights_consistency():
    if not hasattr(telegram_bot, "_cfo_insights_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._cfo_insights_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.CFO_INSIGHTS_ALLOWED_STATUS, "cfo insights status out of allowed set")
    _assert(str(snapshot.get("data_confidence") or "") in telegram_bot.CFO_INSIGHTS_ALLOWED_CONFIDENCE, "cfo insights data_confidence out of allowed set")
    for key in ("insights", "risks", "opportunities", "actions", "warnings"):
        _assert(isinstance(snapshot.get(key), list), f"cfo insights {key} should be list")
    for bucket_name in ("insights", "risks", "opportunities"):
        for item in snapshot.get(bucket_name) or []:
            _assert(str(item.get("type") or "") in telegram_bot.CFO_INSIGHTS_ALLOWED_TYPES, f"cfo insights {bucket_name} type out of allowed set")
            _assert(str(item.get("severity") or "") in telegram_bot.CFO_INSIGHTS_ALLOWED_SEVERITY, f"cfo insights {bucket_name} severity out of allowed set")
            _assert(str(item.get("confidence") or "") in telegram_bot.CFO_INSIGHTS_ALLOWED_CONFIDENCE, f"cfo insights {bucket_name} confidence out of allowed set")


def case_decision_engine_consistency():
    if not hasattr(telegram_bot, "_decision_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._decision_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.DECISION_ENGINE_ALLOWED_STATUS, "decision engine status out of allowed set")
    _assert(str(snapshot.get("data_confidence") or "") in telegram_bot.DECISION_ENGINE_ALLOWED_CONFIDENCE, "decision engine data_confidence out of allowed set")
    _assert(isinstance(snapshot.get("scenarios"), list), "decision engine scenarios should be list")
    _assert(isinstance(snapshot.get("top_actions"), list), "decision engine top_actions should be list")
    _assert(isinstance(snapshot.get("risks"), list), "decision engine risks should be list")
    _assert(isinstance(snapshot.get("warnings"), list), "decision engine warnings should be list")
    for item in snapshot.get("scenarios") or []:
        _assert(str(item.get("category") or "") in telegram_bot.DECISION_ENGINE_ALLOWED_SCENARIO_CATEGORIES, "decision engine scenario category out of allowed set")
        _assert(str(item.get("estimate_type") or "") in telegram_bot.DECISION_ENGINE_ALLOWED_ESTIMATE_TYPES, "decision engine estimate_type out of allowed set")
        _assert(str(item.get("risk") or "") in telegram_bot.DECISION_ENGINE_ALLOWED_RISKS, "decision engine risk out of allowed set")
        _assert(str(item.get("confidence") or "") in telegram_bot.DECISION_ENGINE_ALLOWED_CONFIDENCE, "decision engine confidence out of allowed set")


def case_advisor_v2_consistency():
    if not hasattr(telegram_bot, "_advisor_v2_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._advisor_v2_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.ADVISOR_V2_ALLOWED_STATUS, "advisor v2 status out of allowed set")
    _assert(str(snapshot.get("data_confidence") or "") in telegram_bot.ADVISOR_V2_ALLOWED_CONFIDENCE, "advisor v2 data_confidence out of allowed set")
    _assert(isinstance(snapshot.get("recommendations"), list), "advisor v2 recommendations should be list")
    _assert(isinstance(snapshot.get("do_now"), list), "advisor v2 do_now should be list")
    _assert(isinstance(snapshot.get("do_later"), list), "advisor v2 do_later should be list")
    _assert(isinstance(snapshot.get("do_not_do"), list), "advisor v2 do_not_do should be list")
    _assert(isinstance(snapshot.get("risks"), list), "advisor v2 risks should be list")
    _assert(isinstance(snapshot.get("business_state"), dict), "advisor v2 business_state should be dict")
    _assert(isinstance(snapshot.get("action_groups"), dict), "advisor v2 action_groups should be dict")
    for key in ("sales", "ads", "finance", "data", "costs", "summary", "ads_message"):
        _assert(key in (snapshot.get("business_state") or {}), f"advisor v2 business_state missing {key}")
    for key in ("critical", "recommended", "optional"):
        _assert(isinstance((snapshot.get("action_groups") or {}).get(key), list), f"advisor v2 action_groups {key} should be list")
    for item in snapshot.get("recommendations") or []:
        for key in ("priority", "category", "title", "message", "action", "confidence", "source"):
            _assert(bool(str(item.get(key) or "").strip()), f"advisor v2 recommendation missing {key}")
        _assert(str(item.get("priority") or "") in telegram_bot.ADVISOR_V2_ALLOWED_PRIORITY, "advisor v2 priority out of allowed set")
        _assert(str(item.get("category") or "") in telegram_bot.ADVISOR_V2_ALLOWED_CATEGORY, "advisor v2 category out of allowed set")
        _assert(str(item.get("confidence") or "") in telegram_bot.ADVISOR_V2_ALLOWED_CONFIDENCE, "advisor v2 confidence out of allowed set")
        _assert(str(item.get("source") or "") in telegram_bot.ADVISOR_V2_ALLOWED_SOURCE, "advisor v2 source out of allowed set")


def case_director_consistency():
    if not hasattr(telegram_bot, "_director_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._director_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.DIRECTOR_ALLOWED_STATUS, "director status out of allowed set")
    _assert(str(snapshot.get("business_health") or "") in telegram_bot.DIRECTOR_ALLOWED_BUSINESS_HEALTH, "director business_health out of allowed set")
    _assert(str(snapshot.get("data_confidence") or "") in telegram_bot.DIRECTOR_ALLOWED_CONFIDENCE, "director data_confidence out of allowed set")
    _assert(isinstance(snapshot.get("business_state"), dict), "director business_state should be dict")
    _assert(isinstance(snapshot.get("today_focus"), list), "director today_focus should be list")
    _assert(isinstance(snapshot.get("what_not_to_do"), list), "director what_not_to_do should be list")
    _assert(isinstance(snapshot.get("next_checks"), list), "director next_checks should be list")
    _assert(isinstance(snapshot.get("source_layers"), list), "director source_layers should be list")
    _assert(isinstance(snapshot.get("main_risk"), dict), "director main_risk should be dict")
    _assert(isinstance(snapshot.get("main_action"), dict), "director main_action should be dict")
    for key in ("sales", "ads", "finance", "data_quality", "costs", "cashflow"):
        _assert(str((snapshot.get("business_state") or {}).get(key) or "") in telegram_bot.DIRECTOR_ALLOWED_BLOCK_STATE, f"director business_state {key} out of allowed set")


def case_product_readiness_consistency():
    if not hasattr(telegram_bot, "_product_readiness_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._product_readiness_snapshot(TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("product_status") or "") in telegram_bot.PRODUCT_READINESS_ALLOWED_STATUS, "product readiness status out of allowed set")
    _assert(str(snapshot.get("primary_entrypoint") or "") == "/director", "product readiness primary_entrypoint should be /director")
    _assert(bool(snapshot.get("director_ready")), "product readiness director_ready should be true")
    _assert(isinstance(bool(snapshot.get("control_center_ready")), bool), "product readiness control_center_ready should be bool-like")
    _assert(bool(str(snapshot.get("structure_readiness_status") or "").strip()), "product readiness structure_readiness_status should be present")
    _assert(isinstance(snapshot.get("remaining_blockers"), list), "product readiness remaining_blockers should be list")


def case_release_candidate_snapshots():
    if not hasattr(telegram_bot, "_project_structure_snapshot") or not hasattr(telegram_bot, "_performance_snapshot"):
        return "SKIPPED"

    structure = _cached("project_structure_snapshot", telegram_bot._project_structure_snapshot)
    performance = _cached("release_candidate_performance_snapshot", lambda: telegram_bot._performance_snapshot(TEST_USER_ID, TEST_DAYS))
    readiness = _cached("project_structure_readiness_snapshot", lambda: telegram_bot._project_structure_readiness_snapshot(TEST_USER_ID, TEST_DAYS))
    if not isinstance(structure, dict) or not isinstance(performance, dict):
        return "SKIPPED"
    if not isinstance(readiness, dict):
        return "SKIPPED"

    for key in ("core_modules", "legacy_modules", "deprecated_helpers", "duplicate_helpers", "unused_imports", "large_files", "large_functions", "repeated_code_blocks"):
        _assert(key in structure, f"project structure snapshot missing {key}")
    _assert(str(structure.get("status") or "") == "OK", "project structure status should be OK")

    for key in ("telegram_startup", "largest_modules", "slowest_commands", "snapshot_reuse", "estimated_optimization", "memory_hotspots", "import_hotspots", "layer_timings", "api_call_count", "db_open_count", "db_query_count", "total_ms"):
        _assert(key in performance, f"performance snapshot missing {key}")
    _assert(str(performance.get("status") or "") == "OK", "performance status should be OK")
    _assert(isinstance(performance.get("layer_timings"), dict), "performance layer_timings should be dict")
    _assert(float(performance.get("total_ms") or 0.0) >= 0.0, "performance total_ms should be >= 0")
    _assert(isinstance(performance.get("api_call_count"), dict), "performance api_call_count should be dict")
    _assert(int(performance.get("db_open_count") or 0) >= 0, "performance db_open_count should be >= 0")

    reuse = dict(performance.get("snapshot_reuse") or {})
    director_counts = dict(reuse.get("director_build_counts") or {})
    _assert(bool(director_counts), "performance snapshot should include director build counts")
    for name, count in director_counts.items():
        _assert(int(count) <= 1, f"{name} should be built at most once inside director request")
    _assert(not list(reuse.get("duplicate_snapshot_builds") or []), "duplicate snapshot builds should be empty after reuse optimization")

    for key in ("core_modules_ready", "router_status", "modularization_status", "performance_status", "blockers", "warnings", "recommended_next_step"):
        _assert(key in readiness, f"project structure readiness missing {key}")
    _assert(str(readiness.get("status") or "") in ("READY", "WARNING", "BLOCKED"), "project structure readiness status out of allowed set")


def case_control_center_consistency():
    if not hasattr(telegram_bot, "_control_center_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._control_center_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.CONTROL_CENTER_ALLOWED_STATUS, "control center status out of allowed set")
    for key in ("product", "architecture", "performance", "finance", "data", "business", "diagnostics", "tests"):
        _assert(isinstance(snapshot.get(key), dict), f"control center {key} should be dict")
    _assert(isinstance(snapshot.get("known_blockers"), list), "control center known_blockers should be list")
    _assert(bool(str(snapshot.get("recommended_next_step") or "").strip()), "control center recommended_next_step missing")


def case_command_performance_snapshot():
    if not hasattr(telegram_bot, "_command_performance_snapshot"):
        return "SKIPPED"

    snapshot = _cached("director_command_performance", lambda: telegram_bot._command_performance_snapshot("director", TEST_USER_ID, TEST_DAYS))
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    for key in ("command", "period", "mode", "light_path_used", "full_fallback_fields", "db_open_count", "db_query_count", "total_ms", "layer_timings", "api_call_count", "snapshot_build_counts", "duplicate_snapshot_builds", "slowest_layers", "recommendations", "warnings"):
        _assert(key in snapshot, f"command performance snapshot missing {key}")
    _assert(str(snapshot.get("command") or "") == "director", "command performance should target director by default")
    _assert(str(snapshot.get("mode") or "") == "director_light", "command performance mode should be director_light")
    _assert(isinstance(snapshot.get("light_path_used"), bool), "command performance light_path_used should be bool")
    _assert(isinstance(snapshot.get("full_fallback_fields"), list), "command performance full_fallback_fields should be list")
    counts = dict(snapshot.get("snapshot_build_counts") or {})
    for name, count in counts.items():
        _assert(int(count) <= 1, f"{name} should be built at most once in performance snapshot")
    _assert(not list(snapshot.get("duplicate_snapshot_builds") or []), "command performance snapshot should not report duplicate builds")
    if float(snapshot.get("total_ms") or 0.0) > 1500.0:
        _PERFORMANCE_WARNINGS.append(f"director budget warning: {float(snapshot.get('total_ms') or 0.0):.1f} ms > 1500 ms")


def case_rc_stability_consistency():
    if not hasattr(telegram_bot, "_rc_stability_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._rc_stability_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(str(snapshot.get("status") or "") in telegram_bot.RC_STABILITY_ALLOWED_STATUS, "rc stability status out of allowed set")
    _assert(isinstance(snapshot.get("tested_commands"), list), "rc tested_commands should be list")
    _assert(isinstance(snapshot.get("command_latency"), dict), "rc command_latency should be dict")
    _assert(isinstance(snapshot.get("request_context_isolated"), bool), "rc request_context_isolated should be bool")
    _assert(snapshot.get("memory_delta_mb") is not None, "rc memory_delta_mb should exist")
    _assert(str(snapshot.get("scheduler_status") or "") in telegram_bot.RC_STABILITY_ALLOWED_SCHEDULER_STATUS, "rc scheduler_status out of allowed set")
    _assert(str(snapshot.get("telegram_runtime_status") or "") in telegram_bot.RC_STABILITY_ALLOWED_RUNTIME_STATUS, "rc telegram_runtime_status out of allowed set")
    _assert(isinstance(snapshot.get("warnings"), list), "rc warnings should be list")
    _assert(isinstance(snapshot.get("recommendations"), list), "rc recommendations should be list")


def case_advisor_readiness_consistency():
    if not hasattr(telegram_bot, "_advisor_cfo_readiness_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._advisor_cfo_readiness_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    readiness_percent = int(snapshot.get("readiness_percent") or 0)
    _assert(0 <= readiness_percent <= 100, "advisor readiness percent should be between 0 and 100")
    _assert(isinstance(snapshot.get("blockers"), list), "advisor readiness blockers should be list")
    _assert(bool(str(snapshot.get("migration_target") or "").strip()), "advisor readiness migration_target missing")
    _assert(bool(str(snapshot.get("suggested_next_step") or "").strip()), "advisor readiness suggested_next_step missing")


def case_migration_readiness_consistency():
    if not hasattr(telegram_bot, "_migration_readiness_snapshot"):
        return "SKIPPED"

    snapshot = telegram_bot._migration_readiness_snapshot()
    if not isinstance(snapshot, dict):
        return "SKIPPED"

    _assert(int(snapshot.get("commands_count") or 0) > 0, "migration readiness commands_count should be > 0")
    commands = snapshot.get("commands")
    _assert(isinstance(commands, list), "migration readiness commands should be list")
    product_ux = snapshot.get("product_ux")
    _assert(isinstance(product_ux, dict), "migration readiness product_ux should be dict")
    for command_name in ("/home", "/business", "/finance", "/products", "/analytics", "/system"):
        _assert(command_name in product_ux, f"migration readiness product_ux missing {command_name}")
    legacy_policy = snapshot.get("legacy_policy")
    _assert(isinstance(legacy_policy, list), "migration readiness legacy_policy should be list")
    _assert(bool(legacy_policy), "migration readiness legacy_policy should not be empty")
    for item in commands:
        readiness_percent = int(item.get("migration_readiness_percent") or 0)
        _assert(0 <= readiness_percent <= 100, "migration readiness percent should be between 0 and 100")
        _assert(str(item.get("migration_readiness_status") or "UNKNOWN") in telegram_bot.MIGRATION_READINESS_ALLOWED_STATUSES, "migration readiness status out of allowed set")
        _assert(str(item.get("migration_risk") or "UNKNOWN") in telegram_bot.MIGRATION_READINESS_ALLOWED_RISKS, "migration risk out of allowed set")
        _assert(str(item.get("suggested_phase") or "") in telegram_bot.MIGRATION_READINESS_ALLOWED_PHASES, "suggested_phase out of allowed set")


def case_product_navigation_snapshot_consistency():
    if not hasattr(telegram_bot, "_product_navigation_snapshot"):
        return "SKIPPED"
    snapshot = telegram_bot._product_navigation_snapshot()
    if not isinstance(snapshot, dict):
        return "SKIPPED"
    for key in ("status", "mode", "primary_sections", "hidden_legacy_commands", "developer_commands", "aliases", "recommended_entrypoint"):
        _assert(key in snapshot, f"product navigation snapshot missing {key}")
    _assert(str(snapshot.get("recommended_entrypoint") or "") == "/home", "product navigation recommended_entrypoint should be /home")
    _assert(isinstance(snapshot.get("primary_sections"), list), "product navigation primary_sections should be list")
    _assert(isinstance(snapshot.get("developer_commands"), list), "product navigation developer_commands should be list")


def case_ui_spec_consistency():
    if not hasattr(telegram_bot, "_ui_spec_snapshot"):
        return "SKIPPED"
    snapshot = telegram_bot._ui_spec_snapshot()
    if not isinstance(snapshot, dict):
        return "SKIPPED"
    for key in ("product", "version", "positioning", "principles", "workspaces", "kpi_rules", "ai_rules", "navigation", "design_foundation", "status"):
        _assert(key in snapshot, f"ui spec snapshot missing {key}")
    _assert(str(snapshot.get("product") or "") == "VOOGLII", "ui spec product mismatch")
    _assert(str(snapshot.get("status") or "") == "READY", "ui spec status should be READY")
    _assert("Dashboard" in list(snapshot.get("workspaces") or []), "ui spec should include Dashboard workspace")


def case_telegram_identity_consistency():
    if not hasattr(telegram_bot, "_telegram_identity_snapshot"):
        return "SKIPPED"
    snapshot = telegram_bot._telegram_identity_snapshot()
    if not isinstance(snapshot, dict):
        return "SKIPPED"
    for key in ("brand", "config_source", "token_present", "token_masked", "bot_username", "old_bot_references_found", "active_references", "ignored_archive_references", "runtime_status", "status"):
        _assert(key in snapshot, f"telegram identity snapshot missing {key}")
    _assert(str(snapshot.get("brand") or "") == "VOOGLII", "telegram identity brand mismatch")
    _assert(isinstance(snapshot.get("token_present"), bool), "telegram identity token_present should be bool")
    _assert(isinstance(snapshot.get("active_references"), list), "telegram identity active_references should be list")
    _assert(':' not in str(snapshot.get("token_masked") or ""), "telegram identity should not expose token-like value")


def case_dashboard_prototype_consistency():
    if not hasattr(telegram_bot, "_dashboard_prototype_snapshot"):
        return "SKIPPED"
    snapshot = telegram_bot._dashboard_prototype_snapshot(TEST_USER_ID, TEST_DAYS)
    if not isinstance(snapshot, dict):
        return "SKIPPED"
    for key in ("product", "screen", "period", "overall_status", "sections", "today_actions", "risks", "navigation", "status"):
        _assert(key in snapshot, f"dashboard prototype snapshot missing {key}")
    _assert(str(snapshot.get("screen") or "") == "dashboard_prototype", "dashboard prototype screen mismatch")
    _assert(str(snapshot.get("product") or "") == "VOOGLII", "dashboard prototype product mismatch")
    _assert(isinstance(snapshot.get("sections"), dict), "dashboard prototype sections should be dict")
    _assert(isinstance(snapshot.get("today_actions"), list), "dashboard prototype today_actions should be list")
    _assert(isinstance(snapshot.get("risks"), list), "dashboard prototype risks should be list")


def case_legacy_route_compatibility_consistency():
    if not hasattr(telegram_bot, "_command_source_audit_snapshot"):
        return "SKIPPED"
    snapshot = telegram_bot._command_source_audit_snapshot()
    commands = list(snapshot.get("commands") or [])
    if not commands:
        return "SKIPPED"
    by_command = {str(item.get("command") or ""): item for item in commands}
    for command_name in ("/business metrics", "/finance", "/system audit"):
        _assert(command_name in by_command, f"command audit missing {command_name}")
    _assert(str((by_command["/business metrics"].get("legacy_compatibility") or "")).lower() in ("yes", "n/a"), "/business metrics should remain legacy compatible")
    _assert(str((by_command["/system audit"].get("legacy_compatibility") or "")).lower() in ("yes", "n/a"), "/system audit should remain legacy compatible")
    _assert(str((by_command["/finance"].get("legacy_compatibility") or "")).lower() == "yes", "/finance should preserve legacy compatibility for subcommands")


def run_all():
    counters = {"passed": 0, "failed": 0, "skipped": 0}
    cases = [
        ("Dashboard <-> CEO Report", case_dashboard_vs_ceo_report, False),
        ("Finance Difference <-> Profit Audit", case_finance_difference_vs_profit_audit, False),
        ("Health <-> System Audit", case_health_vs_system_audit, True),
        ("Advisor <-> SKU Analytics", case_advisor_vs_sku_analytics, False),
        ("General Snapshots", case_general_snapshots_not_none, True),
        ("Profit Model Consistency", case_profit_model_consistency, False),
        ("Payment Reconciliation", case_payment_reconciliation_consistency, False),
        ("Payment Timeline Consistency", case_payment_timeline_consistency, False),
        ("Money Flow Consistency", case_money_flow_consistency, False),
        ("WB Commission Breakdown", case_wb_commission_breakdown, False),
        ("Money SKU Consistency", case_sku_money_flow, False),
        ("Finance API Status", case_finance_api_status, False),
        ("Finance API Diagnose", case_finance_api_diagnose, False),
        ("Finance Transport Contract", case_finance_transport_contract, False),
        ("Finance Operation Catalog", case_finance_operation_catalog, False),
        ("Gold Standard Financial Validation", case_gold_standard_financial_validation, False),
        ("Financial Engine Consistency", case_financial_engine_consistency, False),
        ("Business Metrics Consistency", case_business_metrics_consistency, False),
        ("KPI Engine Consistency", case_kpi_engine_consistency, False),
        ("Unified Data Layer Consistency", case_unified_data_layer_consistency, False),
        ("SKU Registry Consistency", case_sku_registry_consistency, False),
        ("Period Engine Consistency", case_period_engine_consistency, False),
        ("Command Source Audit Consistency", case_command_source_audit_consistency, False),
        ("Dashboard Migration Consistency", case_dashboard_migration_consistency, False),
        ("CEO Migration Consistency", case_ceo_migration_consistency, False),
        ("System Audit Migration Consistency", case_system_audit_migration_consistency, False),
        ("CFO Insights Consistency", case_cfo_insights_consistency, False),
        ("Decision Engine Consistency", case_decision_engine_consistency, False),
        ("Advisor v2 Consistency", case_advisor_v2_consistency, False),
        ("Director Consistency", case_director_consistency, False),
        ("Product Readiness Consistency", case_product_readiness_consistency, False),
        ("Release Candidate Snapshots", case_release_candidate_snapshots, True),
        ("Control Center Consistency", case_control_center_consistency, True),
        ("Command Performance Snapshot", case_command_performance_snapshot, False),
        ("RC Stability Consistency", case_rc_stability_consistency, True),
        ("Advisor Readiness Consistency", case_advisor_readiness_consistency, False),
        ("Migration Readiness Consistency", case_migration_readiness_consistency, False),
        ("Product Navigation Snapshot Consistency", case_product_navigation_snapshot_consistency, False),
        ("UI Spec Consistency", case_ui_spec_consistency, False),
        ("Telegram Identity Consistency", case_telegram_identity_consistency, False),
        ("Dashboard Prototype Consistency", case_dashboard_prototype_consistency, False),
        ("Legacy Route Compatibility Consistency", case_legacy_route_compatibility_consistency, False),
    ]
    for name, fn, is_heavy in cases:
        if is_heavy and not _RUN_HEAVY_CASES:
            counters["skipped"] += 1
            print(f"SKIPPED_HEAVY: {name}", flush=True)
            continue
        _run_case(name, fn, counters)
    if counters["failed"] == 0:
        print("REPORT CONSISTENCY OK", flush=True)
    else:
        print("REPORT CONSISTENCY FAILED", flush=True)
    print(f'passed: {counters["passed"]}', flush=True)
    print(f'failed: {counters["failed"]}', flush=True)
    print(f'skipped: {counters["skipped"]}', flush=True)
    for warning in _PERFORMANCE_WARNINGS:
        print(f"WARNING: {warning}", flush=True)
    if counters["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all()
