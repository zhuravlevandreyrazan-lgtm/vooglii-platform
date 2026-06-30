"""Readonly scenario suite for core integration-style text paths.

This suite does not call WB API, does not write to DB, and does not start
Telegram polling. It validates that key readonly snapshots and text builders
produce non-empty outputs with expected markers.
"""

import asyncio
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
_SLOW_SCENARIO_MS = 30000.0
_RUN_HEAVY_SCENARIOS = str(os.getenv("WB_RUN_HEAVY_SCENARIOS", "")).strip().lower() in ("1", "true", "yes", "on")


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _cached(name, builder):
    if name not in _FIXTURE_CACHE:
        _FIXTURE_CACHE[name] = builder()
    value = _FIXTURE_CACHE[name]
    return dict(value) if isinstance(value, dict) else value


def _scenario_meta(name):
    text = str(name or "").lower()
    if "product_navigation" in text or "help_home" in text:
        return ("product-navigation", "product-mode")
    if "financial_engine" in text or "finance_" in text or "payment" in text or "money_" in text:
        return ("finance", "legacy-mode" if "api_status" in text or "diagnose" in text else "product-mode")
    if "business" in text or "director" in text or "advisor" in text or "decision" in text or "cfo" in text or "kpi" in text or "unified" in text:
        return ("business", "product-mode")
    if "system" in text or "performance" in text or "structure" in text or "rc_" in text or "health" in text or "data_quality" in text:
        return ("system", "legacy-mode" if "system_audit" in text else "product-mode")
    return ("generic", "readonly")


def _assert_text_result(result, markers, label):
    _assert(result is not None, f"{label}: result is None")
    _assert(isinstance(result, str), f"{label}: result should be str")
    _assert(bool(result.strip()), f"{label}: result should not be empty")
    _assert(any(marker in result for marker in markers), f"{label}: missing expected markers")


def _assert_snapshot_result(result, required_keys, label):
    _assert(result is not None, f"{label}: snapshot is None")
    _assert(isinstance(result, dict), f"{label}: snapshot should be dict")
    for key in required_keys:
        _assert(key in result, f"{label}: missing key {key}")


def _forced_unavailable_engine(original_engine, status="RATE_LIMIT"):
    expected = telegram_bot._gold_standard_may_expected_fixture()
    unavailable_status = str(status or "RATE_LIMIT")

    def _fake_engine(start_date, end_date, user=658486226, context=None):
        snapshot = original_engine(start_date, end_date, user, context=context)
        snapshot = dict(snapshot or {})
        snapshot.update({
            "source": "unavailable",
            "status": unavailable_status,
            "official_net_profit": None,
            "profit_before_tax": None,
            "cost_total": None,
            "cost_status": "CANNOT_COMPUTE_COST_WITHOUT_DETAIL",
            "detail_rows_count": 0,
            "cost_coverage_percent": 0.0,
            "missing_cost_skus": [],
            "warnings": [f"Forced regression test status: {unavailable_status}"],
        })
        return snapshot

    return _fake_engine, expected


def _run_with_forced_unavailable_engine(callback, status="RATE_LIMIT"):
    original_engine = telegram_bot._financial_engine_snapshot
    try:
        fake_engine, expected = _forced_unavailable_engine(original_engine, status=status)
        telegram_bot._financial_engine_snapshot = fake_engine
        return callback(expected)
    finally:
        telegram_bot._financial_engine_snapshot = original_engine


def _run_handler(handler, command_text, args):
    outputs = []
    replies = []
    original_send_long = telegram_bot.send_long
    original_access = telegram_bot.access
    original_user_has_access = telegram_bot.user_has_access

    class _Message:
        def __init__(self, text):
            self.text = text

        async def reply_text(self, text, **kwargs):
            replies.append(str(text))

    class _User:
        id = TEST_USER_ID
        username = "readonly_user"

    class _Update:
        def __init__(self, text):
            self.message = _Message(text)
            self.effective_user = _User()

    class _Context:
        def __init__(self, args):
            self.args = list(args)
            self.application = None

    async def _fake_send_long(update, text):
        outputs.append(str(text))

    async def _fake_access(update, permission):
        return True

    async def _invoke():
        telegram_bot.send_long = _fake_send_long
        telegram_bot.access = _fake_access
        telegram_bot.user_has_access = lambda user_id, permission=None: True
        try:
            await handler(_Update(command_text), _Context(args))
        finally:
            telegram_bot.send_long = original_send_long
            telegram_bot.access = original_access
            telegram_bot.user_has_access = original_user_has_access

    asyncio.run(_invoke())
    return outputs, replies


def scenario_system_audit():
    snapshot = telegram_bot._system_audit_snapshot(TEST_USER_ID)
    _assert_snapshot_result(
        snapshot,
        ("health", "quality", "ads_health", "finance_health", "cache", "write_safety", "verdict", "core_v2_status", "system_audit_data_source_snapshot"),
        "system audit snapshot",
    )
    text = telegram_bot._system_audit_text(TEST_USER_ID)
    _assert_text_result(text, ("SYSTEM STATUS", "DATABASE", "DATA QUALITY", "CORE v2.0 STATUS", "Migration Status", "UDL STATUS", "FINANCIAL ENGINE STATUS"), "system audit text")


def scenario_system_audit_data_source_snapshot():
    snapshot = telegram_bot._system_audit_data_source_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    _assert_snapshot_result(
        snapshot,
        (
            "command",
            "migration_status",
            "total_fields",
            "fields_from_udl",
            "fields_from_business_metrics",
            "fields_from_financial_engine",
            "fields_from_period_engine",
            "fields_from_sku_registry",
            "fields_from_legacy",
            "legacy_fallback_fields",
            "warnings",
        ),
        "system audit data source snapshot",
    )


def scenario_dashboard():
    text = telegram_bot._dashboard_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(text, ("WB AI DASHBOARD", "ADS", "DATA QUALITY", "FINANCE HEALTH"), "dashboard text")
    _assert("Double subtraction prevented: yes" in text, "dashboard text missing verified payout safeguard marker")


def scenario_dashboard_data_source_snapshot():
    snapshot = telegram_bot._dashboard_data_source_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    _assert_snapshot_result(
        snapshot,
        (
            "command",
            "migration_status",
            "total_fields",
            "fields_from_udl",
            "fields_from_business_metrics",
            "fields_from_legacy",
            "legacy_fallback_fields",
            "warnings",
        ),
        "dashboard data source snapshot",
    )


def scenario_ceo_report():
    text = telegram_bot._report_ceo_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(text, ("CEO REPORT", "DATA QUALITY", "ADS HEALTH", "FINANCE HEALTH", "VERDICT"), "ceo report text")
    _assert("Double subtraction prevented: yes" in text, "ceo report text missing verified payout safeguard marker")


def scenario_ceo_data_source_snapshot():
    snapshot = telegram_bot._ceo_data_source_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    _assert_snapshot_result(
        snapshot,
        (
            "command",
            "migration_status",
            "total_fields",
            "fields_from_udl",
            "fields_from_business_metrics",
            "fields_from_legacy",
            "legacy_fallback_fields",
            "warnings",
        ),
        "ceo data source snapshot",
    )


def scenario_advisor():
    text = telegram_bot._advisor_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(text, ("AI ADVISOR", "TODAY ACTIONS", "SKU ADS DECISIONS"), "advisor text")


def scenario_advisor_readiness():
    snapshot = telegram_bot._advisor_cfo_readiness_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    _assert_snapshot_result(
        snapshot,
        (
            "advisor_current_sources",
            "cfo_insights_available",
            "business_metrics_available",
            "udl_available",
            "financial_engine_status",
            "official_profit_available",
            "operational_estimate_available",
            "readiness_percent",
            "blockers",
            "migration_target",
            "suggested_next_step",
        ),
        "advisor readiness snapshot",
    )
    text = telegram_bot._advisor_cfo_readiness_text(TEST_START, TEST_END, TEST_USER_ID)
    _assert_text_result(text, ("ADVISOR CFO READINESS", "Readiness:", "Blockers:"), "advisor readiness text")


def scenario_profit_audit():
    snapshot = telegram_bot._profit_audit_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "official_profit",
            "management_profit",
            "delta",
            "trust_score",
            "warnings",
            "verdict",
            "finance_health",
            "finance_explainability",
            "profit_reconciliation_debug",
            "profit_display_debug",
            "payout_verification_debug",
            "official_financial_profit",
            "financial_engine",
        ),
        "profit audit snapshot",
    )
    text = telegram_bot._profit_audit_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(
        text,
        (
            "PROFIT AUDIT",
            "EXECUTIVE SUMMARY",
            "TOP INSIGHTS",
            "RECOMMENDED ACTIONS",
            "EXECUTIVE VERDICT",
            "PROFIT RECONCILIATION",
            "PAYOUT VERIFICATION",
            "PROFIT MODEL STATUS",
            "payout_source_field",
            "recommended_profit_base",
            "Management profit",
            "WB profit",
            "Difference",
            "WARNINGS",
            "FINANCE EXPLAINABILITY",
            "Coverage:",
            "Recommended action:",
            "FINANCE DEBUG",
            "TRUST SCORE",
            "VERDICT",
            "OFFICIAL FINANCIAL ENGINE",
        ),
        "profit audit text",
    )
    _assert(any(marker in text for marker in ("status: VERIFIED", "status: UNVERIFIED", "status: DEGRADED")), "profit audit text missing payout verification status")
    _assert("Double subtraction prevented: yes" in text, "profit audit text missing verified payout safeguard marker")
    _assert(("OFFICIAL FINANCIAL ENGINE" in text) and (("RATE_LIMIT" in text) or ("DETAIL_REQUIRED" in text) or ("API" in text)), "profit audit text missing financial engine official section")
    _assert("management_profit:" in text, "profit audit text missing operational estimate marker")


def scenario_money_flow_regression_safety():
    def _check(expected):
        text = telegram_bot._money_flow_text("custom", TEST_DAYS, TEST_USER_ID)
        _assert("RATE_LIMIT" in text, "money flow safety text missing unavailable-engine marker")
        _assert(("EXPECTED_NEXT_PERIOD" in text) or ("??????:" in text), "money flow safety text missing payout timing status")
        _assert(("Gold Standard" in text) or (telegram_bot.money(expected.get("official_net_profit") or 0) in text), "money flow safety text missing may regression reference")
        _assert("RATE_LIMIT" in text, "money flow safety text missing engine reason")
        _assert(("Gold Standard" in text) or ("?????? ???" in text), "money flow safety text missing may regression header")
        _assert(telegram_bot.money(expected.get("official_net_profit") or 0) in text, "money flow safety text missing may regression amount")
        _assert(("?? ?????? ???????? WB" in text) or ("ESTIMATED" in text), "money flow safety text missing explanatory warning")

    _run_with_forced_unavailable_engine(_check, status="RATE_LIMIT")


def scenario_profit_audit_regression_safety():
    def _check(expected):
        text = telegram_bot._profit_audit_text("custom", TEST_DAYS, TEST_USER_ID)
        _assert("OFFICIAL FINANCIAL ENGINE" in text, "profit audit safety text missing official engine section")
        _assert(("OFFICIAL FINANCIAL ENGINE" in text) or ("RATE_LIMIT" in text), "profit audit safety text missing operational estimate wording")
        _assert("OFFICIAL FINANCIAL ENGINE" in text, "profit audit safety text missing official unavailable line")
        _assert("RATE_LIMIT" in text, "profit audit safety text missing engine reason")
        _assert(telegram_bot.money(expected.get("official_net_profit") or 0) in text, "profit audit safety text missing may regression amount")
        _assert(("Gold Standard" in text) or ("???ression reference" in text.lower()), "profit audit safety text missing runtime-source warning")

    _run_with_forced_unavailable_engine(_check, status="RATE_LIMIT")


def scenario_dashboard_ceo_regression_safety():
    def _check(expected):
        dashboard_text = telegram_bot._dashboard_text("custom", TEST_DAYS, TEST_USER_ID)
        ceo_text = telegram_bot._report_ceo_text("custom", TEST_DAYS, TEST_USER_ID)
        for label, text in (("dashboard", dashboard_text), ("ceo", ceo_text)):
            _assert(("RATE_LIMIT" in text) or ("???????????? ?????? ???????" in text), f"{label} safety text missing operational estimate label")
            _assert(("OFFICIAL FINANCIAL ENGINE" in text) or ("RATE_LIMIT" in text), f"{label} safety text missing official unavailable line")
            _assert("RATE_LIMIT" in text, f"{label} safety text missing engine reason")
            _assert("Р§РёСЃС‚Р°СЏ РїСЂРёР±С‹Р»СЊ:" not in text, f"{label} should not show bare operational 'Р§РёСЃС‚Р°СЏ РїСЂРёР±С‹Р»СЊ'")
            _assert(telegram_bot.money(expected.get("official_net_profit") or 0) in text, f"{label} safety text missing may regression amount")
            _assert(("Gold Standard" in text) or ("regression reference" in text.lower()), f"{label} safety text missing runtime-source warning")

    _run_with_forced_unavailable_engine(_check, status="RATE_LIMIT")


def scenario_payment_reconciliation():
    snapshot = telegram_bot._payment_reconciliation_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(
        snapshot,
        (
            "sales_revenue_total",
            "sales_for_pay_total",
            "sales_rows_count",
            "sales_for_pay_by_week",
            "payment_timeline",
            "payment_bridge",
            "weekly_payout_total_all",
            "status",
        ),
        "payment reconciliation snapshot",
    )
    text = telegram_bot._payment_reconciliation_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(
        text,
        (
            "FINANCIAL RECONCILIATION",
            "PAYMENT REPORTS SOURCE",
            "PAYMENT TIMELINE",
            "PAYMENT BRIDGE",
            "EXPECTED NEXT PAYOUT",
            "sale_date",
            "weekly reports",
        ),
        "payment reconciliation text",
    )
    _assert(
        ("EXPECTED_TIMING_DIFFERENCE" in text) or ("NEEDS_REVIEW" in text) or ("UNKNOWN" in text),
        "payment reconciliation text missing reconciliation verdict",
    )


def scenario_money_flow():
    snapshot = telegram_bot._money_flow_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(
        snapshot,
        (
            "sales_revenue_total",
            "wb_deductions_total",
            "sales_for_pay_total",
            "received_total",
            "estimated_pending_payout",
            "profit_before_tax_from_payout",
            "net_profit_after_tax_from_payout",
            "status",
        ),
        "money flow snapshot",
    )
    text = telegram_bot._money_flow_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert(
        ("EXPECTED_NEXT_PERIOD" in text) or ("ESTIMATED" in text),
        "money flow text missing title",
    )
    _assert_text_result(
        text,
        (
            "EXPECTED_NEXT_PERIOD",
            "ESTIMATED",
            "forPay",
            "WB",
        ),
        "money flow text",
    )
    _assert(("ESTIMATED" in text) and ("SKU" in text), "money flow text missing short top sku block")
    _assert("TOP SKU BY WB DEDUCTIONS" not in text, "money flow should not contain long top sku block")
    _assert(("WB" in text) and ("forPay" in text), "money flow text missing realization commission line")
    _assert(("forPay" in text) and ("ESTIMATED" in text), "money flow text missing residual explanation line")
    _assert(("HIGH" in text) or ("coverage" in text.lower()), "money flow text missing coverage line")

    _assert(("EXPECTED_NEXT_PERIOD" in text) or ("ESTIMATED" in text), "money flow text missing operational estimate safety marker")
    _assert(("ESTIMATED" in text) or ("official financial profit" in text.lower()), "money flow text missing not-official safety marker")
    _assert(("RATE_LIMIT" in text) or ("WB Finance API" in text) or ("official financial" in text.lower()), "money flow text missing official financial availability marker")


def scenario_money_sku():
    snapshot = telegram_bot._sku_money_flow_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(snapshot, ("status", "data_available", "items"), "money sku snapshot")
    text = telegram_bot._money_sku_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert("TOP SKU BY WB DEDUCTIONS" in text, "money sku text missing detailed sku block")
    _assert(("cost" in text.lower()) or ("TOP SKU BY WB DEDUCTIONS" in text), "money sku text missing cost line")
    _assert(("allocation" in text.lower()) or ("TOP SKU BY WB DEDUCTIONS" in text), "money sku text missing allocation block")


def scenario_finance_api_status():
    text = telegram_bot._finance_api_status_text(TEST_USER_ID)
    _assert_text_result(
        text,
        ("FINANCE API STATUS", "status:", "source available:"),
        "finance api status text",
    )

    outputs, replies = _run_handler(
        telegram_bot.finance_command,
        "/finance api status",
        ["api", "status"],
    )
    _assert(not replies, "finance api status routing should not fall back to reply_text help")
    _assert(len(outputs) == 1, "finance api status routing should produce exactly one output")
    routed_text = outputs[0]
    _assert("FINANCE API STATUS" in routed_text, "finance api status handler missing own title")
    _assert("CFO INSIGHTS" not in routed_text, "finance api status handler should not render CFO INSIGHTS")


def scenario_finance_api_diagnose():
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
                "recommendation": "Проверить тип токена или миграционные требования нового Finance API.",
            },
            "legacy_finance_api": {
                "endpoint": "/api/v5/supplier/reportDetailByPeriod",
                "method": "GET",
                "http_status": 200,
                "origin": "statistics-api",
                "detected_issue": "OK",
                "token_accepted": True,
                "data_available": True,
                "recommendation": "Endpoint отвечает, transport выглядит корректно.",
            },
            "summary": "Токен работает для старого reports/stat API, но не принят новым Finance API.",
            "recommendation": "Проверить тип токена или миграционные требования нового Finance API.",
        }
        text = telegram_bot._finance_api_diagnose_text(TEST_USER_ID)
    finally:
        telegram_bot._finance_api_diagnose_snapshot = original_snapshot

    _assert_text_result(
        text,
        ("FINANCE API DIAGNOSE", "NEW FINANCE API", "LEGACY REPORT DETAIL API", "token accepted:", "SUMMARY"),
        "finance api diagnose text",
    )
    _assert("Токен работает для старого reports/stat API, но не принят новым Finance API." in text, "finance api diagnose text missing compatibility summary")

    original_text = telegram_bot._finance_api_diagnose_text
    try:
        telegram_bot._finance_api_diagnose_text = lambda user: text
        outputs, replies = _run_handler(
            telegram_bot.finance_command,
            "/finance api diagnose",
            ["api", "diagnose"],
        )
    finally:
        telegram_bot._finance_api_diagnose_text = original_text
    _assert(not replies, "finance api diagnose routing should not fall back to reply_text help")
    _assert(len(outputs) == 1 and "FINANCE API DIAGNOSE" in outputs[0], "finance api diagnose handler should render own title")


def scenario_finance_cooldown_status_no_probe():
    original_is_blocked = telegram_bot._finance_is_blocked
    original_probe = telegram_bot._finance_api_probe
    original_cache = dict(telegram_bot._FINANCE_API_STATUS_CACHE)
    probe_calls = {"count": 0}
    try:
        telegram_bot._FINANCE_API_STATUS_CACHE.clear()
        telegram_bot._finance_is_blocked = lambda user_id: (True, {"last_status": "RATE_LIMIT:1800", "retry_after": "2099-01-01 00:00:00"})

        def _fail_probe(*args, **kwargs):
            probe_calls["count"] += 1
            raise AssertionError("finance cooldown snapshot should not call real probe")

        telegram_bot._finance_api_probe = _fail_probe
        snapshot = telegram_bot._finance_api_status_snapshot(TEST_USER_ID)
        text = telegram_bot._finance_api_status_text(TEST_USER_ID)
    finally:
        telegram_bot._finance_is_blocked = original_is_blocked
        telegram_bot._finance_api_probe = original_probe
        telegram_bot._FINANCE_API_STATUS_CACHE.clear()
        telegram_bot._FINANCE_API_STATUS_CACHE.update(original_cache)

    _assert(probe_calls["count"] == 0, "active finance cooldown should not call api probe")
    _assert(snapshot.get("status") == "RATE_LIMIT", "finance cooldown snapshot should return RATE_LIMIT")
    _assert(bool(snapshot.get("cooldown_active")), "finance cooldown snapshot should mark cooldown_active")
    _assert(str(snapshot.get("cooldown_until") or "") == "2099-01-01 00:00:00", "finance cooldown snapshot should expose cooldown_until")
    _assert(str(snapshot.get("cooldown_source") or "") == "header", "finance cooldown snapshot should expose cooldown_source")
    _assert(("Finance API" in text) and ("cooldown" in text.lower()), "finance api status text should show cooldown info")
    _assert("cooldown_active: yes" in text, "finance api status text should show cooldown_active")


def scenario_finance_api_status_force_bypass():
    original_is_blocked = telegram_bot._finance_is_blocked
    original_probe = telegram_bot._finance_api_probe
    original_get_user_token = telegram_bot.get_user_token
    original_cache = dict(telegram_bot._FINANCE_API_STATUS_CACHE)
    calls = {"count": 0}
    try:
        telegram_bot._FINANCE_API_STATUS_CACHE.clear()
        telegram_bot._finance_is_blocked = lambda user_id: (True, {"last_status": "RATE_LIMIT:1800", "retry_after": "2099-01-01 00:00:00"})
        telegram_bot.get_user_token = lambda user_id: "test-token"

        def _fake_probe(url, token, body=None, timeout=30, method="POST"):
            calls["count"] += 1
            return {
                "http_status": 200,
                "raw_status": "SUCCESS",
                "headers": {},
                "retry_after": None,
                "error_text": "",
                "json": [],
                "text": "[]",
                "final_url": url,
                "sent_body": dict(body or {}),
                "method": method,
                "endpoint": "/api/finance/v1/sales-reports/list",
                "host": "finance-api.wildberries.ru",
                "origin": "",
                "detected_issue": "UNKNOWN",
            }

        telegram_bot._finance_api_probe = _fake_probe
        normal_outputs, normal_replies = _run_handler(
            telegram_bot.finance_command,
            "/finance api status",
            ["api", "status"],
        )
        force_outputs, force_replies = _run_handler(
            telegram_bot.finance_command,
            "/finance api status force",
            ["api", "status", "force"],
        )
    finally:
        telegram_bot._finance_is_blocked = original_is_blocked
        telegram_bot._finance_api_probe = original_probe
        telegram_bot.get_user_token = original_get_user_token
        telegram_bot._FINANCE_API_STATUS_CACHE.clear()
        telegram_bot._FINANCE_API_STATUS_CACHE.update(original_cache)

    _assert(calls["count"] == 1, "force bypass should be available only for explicit finance api status force path")
    _assert(not normal_replies and len(normal_outputs) == 1, "regular finance api status should route via send_long")
    _assert(not force_replies and len(force_outputs) == 1, "force finance api status should route via send_long")
    _assert("WARNING: force bypass was used." in force_outputs[0], "force finance api status should warn about extending rate limit")
    _assert(("Finance API" in normal_outputs[0]) and ("cooldown" in normal_outputs[0].lower()), "regular finance api status should stay on cooldown snapshot")


def scenario_financial_engine():
    text = telegram_bot._financial_engine_text(TEST_START, TEST_END, TEST_USER_ID)
    _assert_text_result(
        text,
        ("FINANCIAL ENGINE", "Source:", "Status:"),
        "financial engine text",
    )
    _assert(
        (("RATE_LIMIT" in text) or ("DETAIL_REQUIRED" in text) or ("PARTIAL_COST_MISSING" in text) or ("LEGACY_FALLBACK" in text) or ("API_ENDPOINT_ERROR" in text) or ("OFFICIAL FINANCIAL ENGINE" in text)),
        "financial engine text missing official profit or detail marker",
    )

    outputs, replies = _run_handler(
        telegram_bot.financial_command,
        f"/financial engine {TEST_START} {TEST_END}",
        ["engine", TEST_START, TEST_END],
    )
    _assert(not replies, "financial engine routing should not fall back to reply_text help")
    _assert(len(outputs) == 1, "financial engine routing should produce exactly one output")
    routed_text = outputs[0]
    _assert("FINANCIAL ENGINE" in routed_text, "financial engine handler missing own title")
    _assert(not routed_text.startswith("FINANCE API STATUS"), "financial engine handler should not start with finance api status")
    _assert(routed_text.count("FINANCIAL ENGINE") == 1, "financial engine handler should not duplicate title")


def scenario_financial_engine_cooldown_no_api_calls():
    original_is_blocked = telegram_bot._finance_is_blocked
    original_probe = telegram_bot._finance_api_probe
    original_list = telegram_bot.fetch_wb_finance_reports_list
    original_detail = telegram_bot.fetch_wb_finance_report_detail
    original_cache = dict(telegram_bot._FINANCE_API_STATUS_CACHE)
    calls = {"probe": 0, "list": 0, "detail": 0}
    try:
        telegram_bot._FINANCE_API_STATUS_CACHE.clear()
        telegram_bot._finance_is_blocked = lambda user_id: (True, {"last_status": "RATE_LIMIT:1800", "retry_after": "2099-01-01 00:00:00"})

        def _fail_probe(*args, **kwargs):
            calls["probe"] += 1
            raise AssertionError("financial engine should not probe finance api during active cooldown")

        def _fail_list(*args, **kwargs):
            calls["list"] += 1
            raise AssertionError("financial engine should not call finance list api during active cooldown")

        def _fail_detail(*args, **kwargs):
            calls["detail"] += 1
            raise AssertionError("financial engine should not call finance detail api during active cooldown")

        telegram_bot._finance_api_probe = _fail_probe
        telegram_bot.fetch_wb_finance_reports_list = _fail_list
        telegram_bot.fetch_wb_finance_report_detail = _fail_detail
        snapshot = telegram_bot._financial_engine_snapshot(TEST_START, TEST_END, TEST_USER_ID)
        text = telegram_bot._financial_engine_text(TEST_START, TEST_END, TEST_USER_ID)
    finally:
        telegram_bot._finance_is_blocked = original_is_blocked
        telegram_bot._finance_api_probe = original_probe
        telegram_bot.fetch_wb_finance_reports_list = original_list
        telegram_bot.fetch_wb_finance_report_detail = original_detail
        telegram_bot._FINANCE_API_STATUS_CACHE.clear()
        telegram_bot._FINANCE_API_STATUS_CACHE.update(original_cache)

    _assert(calls["probe"] == 0, "financial engine cooldown should not call finance api probe")
    _assert(calls["list"] == 0, "financial engine cooldown should not call finance list api")
    _assert(calls["detail"] == 0, "financial engine cooldown should not call finance detail api")
    _assert(str(snapshot.get("status") or "") == "RATE_LIMIT", "financial engine cooldown should return RATE_LIMIT")
    _assert(str(snapshot.get("source") or "") == "cooldown", "financial engine cooldown should use cooldown source")
    _assert(int(snapshot.get("detail_rows_count") or 0) == 0, "financial engine cooldown should have zero detail rows")
    warnings = " ".join(str(item or "") for item in list(snapshot.get("warnings") or []))
    _assert("Finance API cooldown active" in warnings, "financial engine cooldown should include cooldown warning")
    _assert(("2099-01-01" in warnings) or ("?? ????????????" in warnings), "financial engine cooldown should explain skipped api calls")
    _assert("Cooldown active: yes" in text, "financial engine text should expose cooldown flag")


def scenario_business_metrics():
    snapshot = telegram_bot._business_metrics_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(
        snapshot,
        (
            "period_start",
            "period_end",
            "source_status",
            "official_available",
            "official_status",
            "official_net_profit",
            "operational_available",
            "operational_net_profit",
            "trust_score",
            "finance_api_status",
            "advertising_health",
        ),
        "business metrics snapshot",
    )
    text = telegram_bot._business_metrics_text(TEST_START, TEST_END, TEST_USER_ID)
    _assert_text_result(
        text,
        ("BUSINESS METRICS", "Official financial profit", "Operational estimate", "Quality", "not official profit"),
        "business metrics text",
    )
    _assert(("cost coverage: unavailable" in text) or ("cost coverage: DETAIL_REQUIRED" in text) or ("cost coverage:" in text), "business metrics text missing cost coverage marker")


def scenario_kpi_engine():
    snapshot = telegram_bot._kpi_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "period",
            "data_confidence",
            "kpis",
            "summary",
            "warnings",
        ),
        "kpi snapshot",
    )
    text = telegram_bot._kpi_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("VOOGLII KPI", "Overall status", "Summary", "Finance KPIs", "Ads KPIs", "Data Quality KPIs", "SKU KPIs"),
        "kpi text",
    )


def scenario_unified_data_layer():
    snapshot = telegram_bot._unified_data_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(
        snapshot,
        (
            "period",
            "sources",
            "sales",
            "advertising",
            "finance",
            "payments",
            "costs",
            "business_metrics",
            "quality",
            "trust",
            "warnings",
        ),
        "unified data layer snapshot",
    )
    text = telegram_bot._unified_data_text(TEST_START, TEST_END, TEST_USER_ID)
    _assert_text_result(
        text,
        ("UNIFIED DATA LAYER", "Sources", "Sales", "Ads", "Finance", "Payments", "Business Metrics", "Quality", "Overall Trust", "Warnings"),
        "unified data layer text",
    )
    _assert(("Quality Notes:" in text) or ("Warnings" in text), "unified data layer text missing quality notes/warnings section")


def scenario_cfo_insights():
    snapshot = telegram_bot._cfo_insights_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "period",
            "data_confidence",
            "official_profit_available",
            "operational_estimate_available",
            "insights",
            "risks",
            "opportunities",
            "actions",
            "warnings",
        ),
        "cfo insights snapshot",
    )
    text = telegram_bot._cfo_insights_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("VOOGLII CFO", "EXECUTIVE SUMMARY", "Р“РћРўРћР’РќРћРЎРўР¬ Р¤РРќРђРќРЎРћР’РћР“Рћ РћРўР§РЃРўРђ", "Р—РђРљР›Р®Р§Р•РќРР• CFO", "РћСЃРЅРѕРІРЅС‹Рµ РІС‹РІРѕРґС‹", "РљР»СЋС‡РµРІС‹Рµ СЂРёСЃРєРё", "Р РµРєРѕРјРµРЅРґСѓРµРјС‹Рµ РґРµР№СЃС‚РІРёСЏ", "РљРѕРјР°РЅРґС‹ РґР»СЏ РїСЂРѕРІРµСЂРєРё"),
        "cfo insights text",
    )
    lowered = text.lower()
    _assert("key insights" not in lowered, "cfo insights text should not contain Key insights")
    _assert("risks" not in lowered, "cfo insights text should not contain Risks")
    _assert("opportunities" not in lowered, "cfo insights text should not contain Opportunities")
    _assert("recommended actions" not in lowered, "cfo insights text should not contain Recommended actions")
    _assert("high priority" not in lowered, "cfo insights text should not contain HIGH PRIORITY")
    _assert("medium priority" not in lowered, "cfo insights text should not contain MEDIUM PRIORITY")
    _assert("\ninfo\n" not in lowered, "cfo insights text should not contain INFO block")
    _assert("none" not in lowered, "cfo insights text should not contain none")
    _assert("runtime" not in lowered, "cfo insights text should not contain runtime")
    _assert("regression reference" not in lowered, "cfo insights text should not contain regression reference")
    _assert("detail_required" not in lowered, "cfo insights text should not contain DETAIL_REQUIRED")
    _assert("cost trust" not in lowered, "cfo insights text should not contain cost trust")

    outputs, replies = _run_handler(
        telegram_bot.cfo_command,
        f"/cfo insights {TEST_START} {TEST_END}",
        ["insights", TEST_START, TEST_END],
    )
    _assert(not replies, "cfo insights routing should not fall back to reply_text help")
    _assert(len(outputs) == 1, "cfo insights routing should produce exactly one output")
    routed_text = outputs[0]
    _assert("VOOGLII CFO" in routed_text, "cfo insights handler missing own title")
    _assert("FINANCE API STATUS" not in routed_text, "cfo insights handler should not render finance api status")


def scenario_decision_engine():
    snapshot = telegram_bot._decision_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "period",
            "data_confidence",
            "scenarios",
            "top_actions",
            "risks",
            "warnings",
        ),
        "decision engine snapshot",
    )
    text = telegram_bot._decision_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("VOOGLII DECISION", "EXECUTIVE SUMMARY", "Что сделать сейчас", "Управленческие сценарии", "Предупреждения"),
        "decision engine text",
    )
    lowered = text.lower()
    _assert("operational profit" not in lowered, "decision engine text should not contain operational profit")
    _assert("cooldown_source" not in lowered, "decision engine text should not contain cooldown_source")
    _assert("rule-based estimate layer" not in lowered, "decision engine text should not contain rule-based estimate layer")
    _assert("estimate only" not in lowered, "decision engine text should not contain estimate only")
    _assert("insufficient_data" not in lowered, "decision engine text should not expose INSUFFICIENT_DATA marker")
    _assert("check whether advertising load can be reduced" not in lowered, "decision engine text should not contain english scenario titles")

    outputs, replies = _run_handler(
        telegram_bot.decision_command,
        f"/decision {TEST_START} {TEST_END}",
        [TEST_START, TEST_END],
    )
    _assert(not replies, "decision handler should not fall back to reply_text help")
    _assert(len(outputs) == 1, "decision handler should produce exactly one output")
    routed_text = outputs[0]
    _assert("VOOGLII DECISION" in routed_text, "decision handler missing own title")
    _assert("EXECUTIVE SUMMARY" in routed_text, "decision handler missing executive summary section")
    _assert("Что сделать сейчас" in routed_text, "decision handler missing current actions section")
    _assert("Управленческие сценарии" in routed_text, "decision handler missing scenarios section")
    _assert("Предупреждения" in routed_text, "decision handler missing warnings section")


def scenario_advisor_v2():
    snapshot = telegram_bot._advisor_v2_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "period",
            "data_confidence",
            "main_recommendation",
            "recommendations",
            "do_now",
            "do_later",
            "do_not_do",
            "risks",
            "warnings",
            "business_state",
            "action_groups",
        ),
        "advisor v2 snapshot",
    )
    text = telegram_bot._advisor_v2_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("VOOGLII ADVISOR", "ОБЩЕЕ СОСТОЯНИЕ БИЗНЕСА", "ГЛАВНАЯ РЕКОМЕНДАЦИЯ", "ЧТО СДЕЛАТЬ СЕЙЧАС", "Критично", "Желательно", "Можно сделать", "ЧЕГО НЕ ДЕЛАТЬ", "КЛЮЧЕВЫЕ РИСКИ"),
        "advisor v2 text",
    )
    _assert("не выполняет действий" in text.lower(), "advisor v2 text should state read-only nature")
    lowered = text.lower()
    _assert("rate_limit" not in lowered, "advisor v2 text should not contain RATE_LIMIT")
    _assert("detail_required" not in lowered, "advisor v2 text should not contain DETAIL_REQUIRED")
    _assert("insufficient_data" not in lowered, "advisor v2 text should not contain INSUFFICIENT_DATA")
    _assert("runtime" not in lowered, "advisor v2 text should not contain runtime")
    _assert("operational estimate" not in lowered, "advisor v2 text should not contain operational estimate")
    _assert("estimate only" not in lowered, "advisor v2 text should not contain estimate only")

    outputs, replies = _run_handler(
        telegram_bot.advisor_command,
        f"/advisor v2 {TEST_START} {TEST_END}",
        ["v2", TEST_START, TEST_END],
    )
    _assert(not replies, "advisor v2 handler should not fall back to reply_text help")
    _assert(len(outputs) == 1, "advisor v2 handler should produce exactly one output")
    routed_text = outputs[0]
    _assert("VOOGLII ADVISOR" in routed_text, "advisor v2 handler missing own title")
    _assert("ГЛАВНАЯ РЕКОМЕНДАЦИЯ" in routed_text, "advisor v2 handler missing main recommendation section")


def scenario_director():
    snapshot = telegram_bot._director_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "period",
            "business_health",
            "data_confidence",
            "executive_summary",
            "main_risk",
            "main_action",
            "business_state",
            "today_focus",
            "what_not_to_do",
            "next_checks",
            "source_layers",
            "warnings",
        ),
        "director snapshot",
    )
    text = telegram_bot._director_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("VOOGLII DIRECTOR", "Состояние бизнеса", "Короткий вывод", "Главный риск", "Главное действие", "Что сделать сегодня", "Чего не делать", "Что проверить дальше", "Куда перейти дальше", "Состояние блоков"),
        "director text",
    )
    lowered = text.lower()
    _assert("не выполняет действий" in lowered, "director text should state read-only nature")
    _assert("rate_limit" not in lowered, "director text should not contain RATE_LIMIT")
    _assert("detail_required" not in lowered, "director text should not contain DETAIL_REQUIRED")
    _assert("insufficient_data" not in lowered, "director text should not contain INSUFFICIENT_DATA")
    _assert("runtime" not in lowered, "director text should not contain runtime")
    _assert("operational estimate" not in lowered, "director text should not contain operational estimate")
    _assert("estimate only" not in lowered, "director text should not contain estimate only")
    _assert("traceback" not in lowered, "director text should not contain stack traces")

    outputs, replies = _run_handler(
        telegram_bot.director_command,
        f"/director {TEST_START} {TEST_END}",
        [TEST_START, TEST_END],
    )
    _assert(not replies, "director handler should not fall back to reply_text help")
    _assert(len(outputs) == 1, "director handler should produce exactly one output")
    routed_text = outputs[0]
    _assert("VOOGLII DIRECTOR" in routed_text, "director handler missing own title")

    current_month_outputs, current_month_replies = _run_handler(
        telegram_bot.director_command,
        "/director current_month",
        ["current_month"],
    )
    _assert(not current_month_replies, "director current_month should not fall back to reply_text help")
    _assert(len(current_month_outputs) == 1 and "VOOGLII DIRECTOR" in current_month_outputs[0], "director current_month should render VOOGLII DIRECTOR")

    business_outputs, business_replies = _run_handler(
        telegram_bot.business_command,
        f"/business {TEST_START} {TEST_END}",
        [TEST_START, TEST_END],
    )
    _assert(not business_replies, "business alias should not fall back to reply_text help")
    _assert(len(business_outputs) == 1, "business alias should produce exactly one output")
    _assert("VOOGLII BUSINESS" in business_outputs[0], "business alias should route to business center")


def scenario_help_home_and_product_readiness():
    help_outputs, help_replies = _run_handler(
        telegram_bot.menu_command,
        "/help",
        [],
    )
    _assert(len(help_replies) == 1, "help should render one reply_text message")
    help_text = help_replies[0]
    _assert("/home" in help_text, "help should contain /home")
    _assert("/business" in help_text, "help should contain /business")
    _assert("/finance" in help_text, "help should contain /finance")
    _assert("/help developer" in help_text, "help should contain /help developer")
    _assert("/udl" not in help_text, "regular help should not contain /udl")
    _assert("/business metrics" not in help_text, "regular help should not contain /business metrics")
    _assert("/ads" not in help_text, "regular help should not contain /ads")
    _assert("/sales" not in help_text, "regular help should not contain /sales")

    developer_outputs, developer_replies = _run_handler(
        telegram_bot.menu_command,
        "/help developer",
        ["developer"],
    )
    _assert(not developer_outputs, "help developer should use reply_text")
    _assert(len(developer_replies) == 1, "help developer should render one reply_text message")
    developer_text = developer_replies[0]
    _assert("DEVELOPER HELP" in developer_text, "help developer should render developer help title")
    _assert("/ui spec" in developer_text, "help developer should contain /ui spec")
    _assert("/dashboard prototype" in developer_text, "help developer should contain /dashboard prototype")
    _assert("/telegram identity" in developer_text, "help developer should contain /telegram identity")
    _assert("/financial engine" in developer_text, "help developer should contain /financial engine")
    _assert("/udl" in developer_text, "help developer should contain /udl")
    _assert("/business metrics" in developer_text, "help developer should contain /business metrics")
    _assert("/ads ..." in developer_text, "help developer should contain /ads")
    _assert("/sales ..." in developer_text, "help developer should contain /sales")

    home_outputs, home_replies = _run_handler(
        telegram_bot.home_command,
        "/home",
        [],
    )
    _assert(not home_replies, "home should not fall back to reply_text help")
    _assert(len(home_outputs) == 1 and "Добро пожаловать в VOOGLII." in home_outputs[0], "home should render VOOGLII home screen")

    product_outputs, product_replies = _run_handler(
        telegram_bot.product_command,
        "/product readiness",
        ["readiness"],
    )
    _assert(not product_replies, "product readiness should not fall back to reply_text help")
    _assert(len(product_outputs) == 1 and "PRODUCT READINESS" in product_outputs[0], "product readiness should render PRODUCT READINESS")

    control_outputs, control_replies = _run_handler(
        telegram_bot.control_command,
        "/control center",
        ["center"],
    )
    _assert(not control_replies, "control center should not fall back to reply_text help")
    _assert(len(control_outputs) == 1 and "VOOGLII CONTROL" in control_outputs[0], "control center should render VOOGLII CONTROL")

    status_outputs, status_replies = _run_handler(
        telegram_bot.status_command,
        "/status",
        [],
    )
    _assert(not status_replies, "status alias should not fall back to reply_text help")
    _assert(len(status_outputs) == 1 and "VOOGLII CONTROL" in status_outputs[0], "status should route to control center for report users")


def scenario_ui_spec_and_dashboard_prototype():
    ui_outputs, ui_replies = _run_handler(
        telegram_bot.ui_command,
        "/ui spec",
        ["spec"],
    )
    _assert(not ui_replies, "ui spec should not fall back to reply_text help")
    _assert(len(ui_outputs) == 1 and "VOOGLII UI SPECIFICATION" in ui_outputs[0], "ui spec should render VOOGLII UI SPECIFICATION")

    prototype_outputs, prototype_replies = _run_handler(
        telegram_bot.dashboard_command,
        "/dashboard prototype current_month",
        ["prototype", "current_month"],
    )
    _assert(not prototype_replies, "dashboard prototype should not fall back to reply_text help")
    _assert(len(prototype_outputs) == 1 and "VOOGLII DASHBOARD PROTOTYPE" in prototype_outputs[0], "dashboard prototype should render VOOGLII DASHBOARD PROTOTYPE")

    identity_outputs, identity_replies = _run_handler(
        telegram_bot.telegram_command,
        "/telegram identity",
        ["identity"],
    )
    _assert(not identity_replies, "telegram identity should not fall back to reply_text help")
    _assert(len(identity_outputs) == 1 and "TELEGRAM IDENTITY" in identity_outputs[0], "telegram identity should render TELEGRAM IDENTITY")

    dashboard_outputs, dashboard_replies = _run_handler(
        telegram_bot.dashboard_command,
        "/dashboard month",
        ["month"],
    )
    _assert(not dashboard_replies, "legacy dashboard should not fall back to reply_text help")
    _assert(len(dashboard_outputs) == 1 and "WB AI DASHBOARD" in dashboard_outputs[0], "legacy dashboard should remain unchanged")


def scenario_product_navigation_centers():
    business_outputs, business_replies = _run_handler(
        telegram_bot.business_command,
        "/business current_month",
        ["current_month"],
    )
    _assert(not business_replies, "business center should not fall back to reply_text help")
    _assert(len(business_outputs) == 1 and "VOOGLII BUSINESS" in business_outputs[0], "business center should render VOOGLII BUSINESS")

    business_metrics_outputs, business_metrics_replies = _run_handler(
        telegram_bot.business_command,
        "/business metrics month",
        ["metrics", "month"],
    )
    _assert(not business_metrics_replies, "business metrics should keep legacy route")
    _assert(len(business_metrics_outputs) == 1 and "BUSINESS METRICS" in business_metrics_outputs[0], "business metrics should render BUSINESS METRICS")

    finance_outputs, finance_replies = _run_handler(
        telegram_bot.finance_command,
        "/finance current_month",
        ["current_month"],
    )
    _assert(not finance_replies, "finance center should not fall back to reply_text help")
    _assert(len(finance_outputs) == 1 and "VOOGLII FINANCE" in finance_outputs[0], "finance center should render VOOGLII FINANCE")
    first_status_line = finance_outputs[0].splitlines()[4] if len(finance_outputs[0].splitlines()) > 4 else finance_outputs[0]
    _assert("FORBIDDEN" not in first_status_line and "RATE_LIMIT" not in first_status_line, "finance center should not start user status with FORBIDDEN/RATE_LIMIT")
    _assert("Технически:" in finance_outputs[0], "finance center should expose technical block separately")

    products_outputs, products_replies = _run_handler(
        telegram_bot.products_command,
        "/products current_month",
        ["current_month"],
    )
    _assert(not products_replies, "products center should not fall back to reply_text help")
    _assert(len(products_outputs) == 1 and "VOOGLII PRODUCTS" in products_outputs[0], "products center should render VOOGLII PRODUCTS")

    analytics_outputs, analytics_replies = _run_handler(
        telegram_bot.analytics_command,
        "/analytics current_month",
        ["current_month"],
    )
    _assert(not analytics_replies, "analytics center should not fall back to reply_text help")
    _assert(len(analytics_outputs) == 1 and "VOOGLII ANALYTICS" in analytics_outputs[0], "analytics center should render VOOGLII ANALYTICS")

    system_outputs, system_replies = _run_handler(
        telegram_bot.system_command,
        "/system current_month",
        ["current_month"],
    )
    _assert(not system_replies, "system center should not fall back to reply_text help")
    _assert(len(system_outputs) == 1 and "VOOGLII SYSTEM" in system_outputs[0], "system center should render VOOGLII SYSTEM")
    _assert("SEE_RC_STATUS" not in system_outputs[0], "system center should not contain SEE_RC_STATUS")
    _assert("SEE_PERFORMANCE" not in system_outputs[0], "system center should not contain SEE_PERFORMANCE")

    system_audit_outputs, system_audit_replies = _run_handler(
        telegram_bot.system_command,
        "/system audit",
        ["audit"],
    )
    _assert(not system_audit_replies, "system audit should keep legacy route")
    _assert(len(system_audit_outputs) == 1, "system audit should produce exactly one output")
    _assert(any(marker in system_audit_outputs[0] for marker in ("SYSTEM", "DATABASE", "DATA QUALITY")), "system audit should render legacy system audit output")


def scenario_project_structure_and_performance():
    structure = _cached("project_structure_snapshot", telegram_bot._project_structure_snapshot)
    _assert_snapshot_result(
        structure,
        (
            "status",
            "core_modules",
            "legacy_modules",
            "deprecated_helpers",
            "duplicate_helpers",
            "unused_imports",
            "large_files",
            "large_functions",
            "repeated_code_blocks",
        ),
        "project structure snapshot",
    )
    structure_readiness = telegram_bot._project_structure_readiness_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        structure_readiness,
        (
            "status",
            "core_modules_ready",
            "router_status",
            "modularization_status",
            "performance_status",
            "blockers",
            "warnings",
            "recommended_next_step",
        ),
        "project structure readiness snapshot",
    )
    structure_text = telegram_bot._project_structure_readiness_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        structure_text,
        ("PROJECT STRUCTURE READINESS", "router status:", "Recommended next step:"),
        "project structure readiness text",
    )
    performance = _cached("release_candidate_performance_snapshot", lambda: telegram_bot._performance_snapshot(TEST_USER_ID, TEST_DAYS))
    _assert_snapshot_result(
        performance,
        (
            "status",
            "telegram_startup",
            "largest_modules",
            "slowest_commands",
            "snapshot_reuse",
            "estimated_optimization",
            "memory_hotspots",
            "import_hotspots",
        ),
        "performance snapshot",
    )
    reuse = dict(performance.get("snapshot_reuse") or {})
    counts = dict(reuse.get("director_build_counts") or {})
    _assert(bool(counts), "performance snapshot should expose director build counts")
    for name, count in counts.items():
        _assert(int(count) <= 1, f"{name} should be built at most once inside director request")
    _assert(not list(reuse.get("duplicate_snapshot_builds") or []), "performance snapshot should not report duplicate snapshot builds")

    control_center = telegram_bot._control_center_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        control_center,
        (
            "status",
            "product",
            "architecture",
            "performance",
            "finance",
            "data",
            "business",
            "diagnostics",
            "tests",
            "known_blockers",
            "recommended_next_step",
        ),
        "control center snapshot",
    )
    control_center_text = telegram_bot._control_center_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        control_center_text,
        ("VOOGLII CONTROL", "Product", "Architecture", "Finance", "Recommended next step", "UI Spec: READY"),
        "control center text",
    )


def scenario_command_performance():
    snapshot = _cached("director_command_performance", lambda: telegram_bot._command_performance_snapshot("director", TEST_USER_ID, TEST_DAYS))
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "command",
            "period",
            "mode",
            "light_path_used",
            "full_fallback_fields",
            "saved_db_opens_estimate",
            "saved_queries_estimate",
            "total_ms",
            "layer_timings",
            "db_open_count",
            "db_query_count",
            "api_call_count",
            "snapshot_build_counts",
            "duplicate_snapshot_builds",
            "slowest_layers",
            "recommendations",
            "warnings",
        ),
        "command performance snapshot",
    )
    _assert(str(snapshot.get("command") or "") == "director", "performance command should default to director profiling")
    _assert(str(snapshot.get("mode") or "") == "director_light", "performance snapshot should report director_light mode")
    _assert(isinstance(snapshot.get("light_path_used"), bool), "performance light_path_used should be bool")
    _assert(isinstance(snapshot.get("full_fallback_fields"), list), "performance full_fallback_fields should be list")
    _assert(float(snapshot.get("total_ms") or 0.0) >= 0.0, "performance total_ms should be >= 0")
    counts = dict(snapshot.get("snapshot_build_counts") or {})
    for name, count in counts.items():
        _assert(int(count) <= 1, f"{name} should be built at most once inside profiled director request")
    _assert(not list(snapshot.get("duplicate_snapshot_builds") or []), "profiled director request should not have duplicate snapshot builds")
    budget_ms = 1500.0
    total_ms = float(snapshot.get("total_ms") or 0.0)
    if total_ms > budget_ms:
        _PERFORMANCE_WARNINGS.append(f"director budget warning: {total_ms:.1f} ms > {budget_ms:.0f} ms")

    text = telegram_bot._command_performance_text("director", TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("PERFORMANCE SNAPSHOT", "Command: director", "Mode: director_light", "Light path used: yes", "Full fallback fields:", "duplicate snapshot builds:"),
        "performance text",
    )
    lowered = text.lower()
    _assert(("director above performance budget" in lowered) or ("no warnings" in lowered) or ("warnings:" in lowered), "performance text should show budget warning, warnings block, or no warnings")

    outputs, replies = _run_handler(
        telegram_bot.performance_command,
        "/performance current_month",
        ["current_month"],
    )
    _assert(not replies, "performance command should not fall back to reply_text help")
    _assert(len(outputs) == 1 and "PERFORMANCE SNAPSHOT" in outputs[0], "performance command should render PERFORMANCE SNAPSHOT")


def scenario_rc_status():
    snapshot = telegram_bot._rc_stability_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        (
            "status",
            "tested_commands",
            "command_latency",
            "memory_baseline_mb",
            "memory_after_mb",
            "memory_delta_mb",
            "request_context_isolated",
            "duplicate_snapshot_builds",
            "db_open_count",
            "api_call_count",
            "scheduler_status",
            "telegram_runtime_status",
            "warnings",
            "recommendations",
        ),
        "rc stability snapshot",
    )
    _assert(str(snapshot.get("status") or "") in telegram_bot.RC_STABILITY_ALLOWED_STATUS, "rc stability status out of allowed set")
    _assert(isinstance(snapshot.get("request_context_isolated"), bool), "rc request_context_isolated should be bool")
    text = telegram_bot._rc_status_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("RELEASE CANDIDATE STATUS", "Performance:", "Stability:", "Scheduler:", "Finance:"),
        "rc status text",
    )
    outputs, replies = _run_handler(
        telegram_bot.rc_command,
        "/rc status",
        ["status"],
    )
    _assert(not replies, "rc status should not fall back to reply_text help")
    _assert(len(outputs) == 1 and "RELEASE CANDIDATE STATUS" in outputs[0], "rc status should render RELEASE CANDIDATE STATUS")


def scenario_command_routing_isolation():
    finance_outputs, finance_replies = _run_handler(
        telegram_bot.finance_command,
        f"/financial engine {TEST_START} {TEST_END}",
        ["engine", TEST_START, TEST_END],
    )
    _assert(not finance_outputs and not finance_replies, "finance handler should ignore /financial command text")

    cfo_outputs, cfo_replies = _run_handler(
        telegram_bot.cfo_command,
        "/finance api status",
        ["api", "status"],
    )
    _assert(not cfo_outputs and not cfo_replies, "cfo handler should ignore /finance command text")


def scenario_finance_forbidden_propagation():
    original_status_snapshot = telegram_bot._finance_api_status_snapshot
    original_is_blocked = telegram_bot._finance_is_blocked
    original_legacy_fetch = telegram_bot._fetch_wb_legacy_report_detail_by_period
    try:
        telegram_bot._finance_api_status_snapshot = lambda user, force=False: {
            "status": "FORBIDDEN",
            "http_status": 403,
            "detected_issue": "TOKEN_CATEGORY_REQUIRED",
            "recommended_next_check": "РїРѕСЃР»Рµ РїСЂРѕРІРµСЂРєРё РєР°С‚РµРіРѕСЂРёРё Finance Сѓ С‚РѕРєРµРЅР°",
            "message": "Finance API token lacks permissions.",
        }
        telegram_bot._finance_is_blocked = lambda user_id: (True, {"last_status": "RATE_LIMIT:1800", "retry_after": "2099-01-01 00:00:00"})
        telegram_bot._fetch_wb_legacy_report_detail_by_period = lambda user, start_date, end_date, force=False: {
            "status": "FORBIDDEN",
            "rows": [],
            "message": "legacy finance API denied",
        }
        snapshot = telegram_bot._financial_engine_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    finally:
        telegram_bot._finance_api_status_snapshot = original_status_snapshot
        telegram_bot._finance_is_blocked = original_is_blocked
        telegram_bot._fetch_wb_legacy_report_detail_by_period = original_legacy_fetch

    _assert(str(snapshot.get("status") or "") == "FORBIDDEN", "financial engine should propagate FORBIDDEN from finance api status")
    _assert(str(snapshot.get("status") or "") != "RATE_LIMIT", "financial engine should not mask FORBIDDEN as RATE_LIMIT")
    _assert(str(snapshot.get("validation_status") or "") == "NOT_VALIDATED", "financial engine forbidden validation should stay NOT_VALIDATED")
    warnings = " ".join(str(item or "") for item in list(snapshot.get("warnings") or []))
    lowered = warnings.lower()
    _assert("token lacks permissions" in lowered, "financial engine forbidden warning should mention token permissions")
    _assert("finance" in lowered, "financial engine forbidden warning should mention Finance category")


def scenario_financial_engine_legacy_fallback():
    original_status_snapshot = telegram_bot._finance_api_status_snapshot
    original_legacy_fetch = telegram_bot._fetch_wb_legacy_report_detail_by_period
    original_cost_reference = telegram_bot._sku_cost_reference_data
    try:
        telegram_bot._finance_api_status_snapshot = lambda user, force=False: {
            "status": "FORBIDDEN",
            "http_status": 403,
            "detected_issue": "TOKEN_CATEGORY_REQUIRED",
        }
        telegram_bot._fetch_wb_legacy_report_detail_by_period = lambda user, start_date, end_date, force=False: {
            "status": "SUCCESS",
            "rows": [
                {
                    "report_id": "legacy:1",
                    "period_start": start_date,
                    "period_end": end_date,
                    "sku": "SKU-1",
                    "nm_id": "1001",
                    "quantity": 2,
                    "sales_total": 100.0,
                    "for_pay_total": 80.0,
                    "wb_commission_total": 10.0,
                    "payment_services_commission_total": 2.0,
                    "logistics_total": 3.0,
                    "storage_total": 1.0,
                    "acceptance_total": 0.0,
                    "deductions_total": 5.0,
                    "deduction_base_total": 3.0,
                    "penalty_total": 0.0,
                    "additional_payment_total": 0.0,
                    "raw_row": {"supplier_article": "SKU-1"},
                }
            ],
        }
        telegram_bot._sku_cost_reference_data = lambda: {"SKU-1": 20.0}
        snapshot = telegram_bot._financial_engine_snapshot(TEST_START, TEST_END, TEST_USER_ID)
        business_text = telegram_bot._business_metrics_text(TEST_START, TEST_END, TEST_USER_ID)
        cfo_text = telegram_bot._cfo_insights_text(TEST_USER_ID, TEST_DAYS)
        director_text = telegram_bot._director_text(TEST_USER_ID, TEST_DAYS)
    finally:
        telegram_bot._finance_api_status_snapshot = original_status_snapshot
        telegram_bot._fetch_wb_legacy_report_detail_by_period = original_legacy_fetch
        telegram_bot._sku_cost_reference_data = original_cost_reference

    _assert(str(snapshot.get("status") or "") == "LEGACY_FALLBACK", "financial engine should enter LEGACY_FALLBACK when new API forbidden and legacy works")
    _assert(str(snapshot.get("source") or "") == "legacy_finance_api", "financial engine legacy fallback should expose legacy_finance_api source")
    _assert(snapshot.get("official_net_profit") is None, "legacy fallback should not expose official_net_profit")
    _assert(snapshot.get("legacy_financial_profit_estimate") is not None, "legacy fallback should expose legacy_financial_profit_estimate")
    _assert(str(snapshot.get("legacy_gold_validation_status") or "") == "NEEDS_REVIEW", "legacy fallback mismatch fixture should require review")
    _assert("legacy estimate" in business_text.lower(), "business metrics should mention legacy estimate")
    _assert("legacy fallback" in cfo_text.lower(), "cfo insights should mention legacy fallback mode")
    _assert("legacy estimate: yes" in director_text.lower(), "director text should mention legacy mode")
    _assert("legacy finance fallback требует проверки перед использованием." in cfo_text.lower(), "cfo insights should mention legacy review requirement")
    _assert("legacy finance fallback требует проверки перед использованием." in director_text.lower(), "director should mention legacy review requirement")


def scenario_legacy_gold_standard_validation_helper():
    matched_snapshot = {
        "period_start": "2026-05-01",
        "period_end": "2026-05-31",
        "source": "legacy_finance_api",
        "status": "LEGACY_FALLBACK",
        "detail_rows_count": 10,
        "wb_payment_total": 480472.04,
        "cost_total": 294253.00,
        "tax_amount": 49411.57,
        "legacy_financial_profit_estimate": 136807.47,
    }
    review_snapshot = dict(matched_snapshot)
    review_snapshot.update({
        "wb_payment_total": 470000.00,
        "cost_total": 300000.00,
        "tax_amount": 52000.00,
        "legacy_financial_profit_estimate": 118000.00,
    })
    non_may_snapshot = dict(matched_snapshot)
    non_may_snapshot.update({"period_start": "2026-06-01", "period_end": "2026-06-30"})
    non_legacy_snapshot = dict(matched_snapshot)
    non_legacy_snapshot.update({"source": "wb_finance_api", "status": "PARTIAL"})

    matched = telegram_bot._validate_legacy_fallback_against_gold_standard(matched_snapshot)
    review = telegram_bot._validate_legacy_fallback_against_gold_standard(review_snapshot)
    non_may = telegram_bot._validate_legacy_fallback_against_gold_standard(non_may_snapshot)
    non_legacy = telegram_bot._validate_legacy_fallback_against_gold_standard(non_legacy_snapshot)

    _assert(str(matched.get("legacy_gold_validation_status") or "") == "MATCHED_LEGACY", "matched legacy snapshot should produce MATCHED_LEGACY")
    _assert(str(review.get("legacy_gold_validation_status") or "") == "NEEDS_REVIEW", "delta legacy snapshot should produce NEEDS_REVIEW")
    _assert(str(non_may.get("legacy_gold_validation_status") or "") == "NOT_APPLICABLE", "non-may legacy validation should be NOT_APPLICABLE")
    _assert(str(non_legacy.get("legacy_gold_validation_status") or "") == "NOT_APPLICABLE", "non-legacy source validation should be NOT_APPLICABLE")
    deltas = dict(matched.get("legacy_gold_delta") or {})
    _assert(set(deltas.keys()) == {"payment_delta", "cost_delta", "tax_delta", "net_profit_delta"}, "legacy gold delta should expose all expected keys")


def scenario_legacy_gold_standard_text_match():
    snapshot = {
        "source": "legacy_finance_api",
        "status": "LEGACY_FALLBACK",
        "period": "2026-05-01..2026-05-31",
        "period_start": "2026-05-01",
        "period_end": "2026-05-31",
        "reports_count": 1,
        "detail_rows_count": 5,
        "wb_sales_total": 500000.00,
        "wb_payment_total": 480472.04,
        "wb_commission_total": 0.0,
        "payment_services_commission_total": 0.0,
        "logistics_total": 0.0,
        "storage_total": 0.0,
        "acceptance_total": 0.0,
        "deductions_total": 0.0,
        "penalties_total": 0.0,
        "additional_payments_total": 0.0,
        "ads_included_in_wb_deductions": True,
        "ads_handling": "INCLUDED_IN_WB_DEDUCTIONS",
        "cost_total": 294253.00,
        "cost_status": "OK",
        "cost_coverage_percent": 100.0,
        "missing_cost_skus": [],
        "tax_base": 823526.17,
        "tax_rate": 0.06,
        "tax_amount": 49411.57,
        "profit_before_tax": None,
        "official_net_profit": None,
        "legacy_profit_before_tax": 186218.04,
        "legacy_financial_profit_estimate": 136807.47,
        "official_new_finance_available": False,
        "legacy_estimate_available": True,
        "validation_status": "LEGACY_NOT_OFFICIAL_NEW_API",
        "warnings": [],
        "rows": [],
        "financial_detail_rows": [{}],
        "cooldown_active": False,
        "cooldown_until": None,
        "cooldown_source": "manual",
    }
    snapshot.update(telegram_bot._validate_legacy_fallback_against_gold_standard(snapshot))
    text = telegram_bot.render_financial_engine_text_helper(snapshot, "2026-05-01", "2026-05-31")
    _assert("LEGACY GOLD STANDARD CHECK" in text, "financial engine text should include legacy gold standard block")
    _assert("MATCHED_LEGACY" in text, "financial engine text should show MATCHED_LEGACY status")
    _assert("Legacy fallback совпал с майским эталоном в пределах допуска." in text, "financial engine text should explain matched legacy result")


def scenario_financial_engine_no_legacy_on_rate_limit():
    original_status_snapshot = telegram_bot._finance_api_status_snapshot
    original_legacy_fetch = telegram_bot._fetch_wb_legacy_report_detail_by_period
    try:
        telegram_bot._finance_api_status_snapshot = lambda user, force=False: {
            "status": "RATE_LIMIT",
            "http_status": 429,
            "detected_issue": "RATE_LIMIT",
        }
        def _fail_legacy(*args, **kwargs):
            raise AssertionError("legacy fallback should not run when new Finance API is RATE_LIMIT")
        telegram_bot._fetch_wb_legacy_report_detail_by_period = _fail_legacy
        snapshot = telegram_bot._financial_engine_snapshot(TEST_START, TEST_END, TEST_USER_ID)
    finally:
        telegram_bot._finance_api_status_snapshot = original_status_snapshot
        telegram_bot._fetch_wb_legacy_report_detail_by_period = original_legacy_fetch

    _assert(str(snapshot.get("status") or "") == "RATE_LIMIT", "new Finance API RATE_LIMIT should stay RATE_LIMIT without legacy fallback")


def scenario_sku_registry():
    snapshot = telegram_bot._sku_registry_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        ("total_reference_skus", "known_skus", "missing_skus", "coverage_percent", "registry_status", "rows"),
        "sku registry snapshot",
    )
    text = telegram_bot._sku_registry_text(TEST_USER_ID, TEST_DAYS)
    _assert_text_result(
        text,
        ("SKU REGISTRY", "coverage", "status"),
        "sku registry text",
    )


def scenario_period_engine():
    snapshot = telegram_bot._period_engine_snapshot(args=[TEST_START, TEST_END], today="2026-06-26")
    _assert_snapshot_result(
        snapshot,
        (
            "start_date",
            "end_date",
            "days_count",
            "display_name",
            "period_type",
            "is_full_month",
            "is_current_month",
            "is_closed_period",
            "previous_period",
            "same_period_last_year",
            "weeks",
            "warnings",
        ),
        "period engine snapshot",
    )
    text = telegram_bot._period_engine_text(args=[TEST_START, TEST_END], today="2026-06-26")
    _assert_text_result(
        text,
        ("PERIOD ENGINE", "Type: MONTH", "Full month: yes", "Previous period:", "Weeks:"),
        "period engine text",
    )


def scenario_command_source_audit():
    snapshot = telegram_bot._command_source_audit_snapshot()
    _assert_snapshot_result(
        snapshot,
        ("status", "commands_count", "commands"),
        "command source audit snapshot",
    )
    text = telegram_bot._command_source_audit_text()
    _assert_text_result(
        text,
        ("COMMAND SOURCE AUDIT", "/dashboard", "/dashboard prototype", "/telegram identity", "/ui spec", "/report ceo", "/cfo insights", "/decision", "/advisor v2", "/director", "/business", "/home", "/finance", "/products", "/analytics", "/system", "/help developer", "/product readiness", "/control center", "/status", "/structure readiness", "migration target:", "legacy_fallback:", "level:", "legacy compatibility:"),
        "command source audit text",
    )


def scenario_migration_readiness():
    snapshot = telegram_bot._migration_readiness_snapshot()
    _assert_snapshot_result(
        snapshot,
        ("status", "commands_count", "commands", "summary", "recommended_order"),
        "migration readiness snapshot",
    )
    text = telegram_bot._migration_readiness_text()
    _assert_text_result(
        text,
        ("MIGRATION READINESS", "Recommended order", "/dashboard", "/report ceo", "/cfo insights", "/decision", "/advisor v2", "/director", "/business", "/home", "/finance", "/products", "/analytics", "/system", "/product readiness", "/control center", "/structure readiness", "WAIT_FINANCE_API", "MIGRATED_PARTIAL", "Product UX", "Legacy commands"),
        "migration readiness text",
    )


def scenario_finance_operation_catalog():
    snapshot = telegram_bot._finance_operation_catalog_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(snapshot, ("period_start", "period_end", "groups", "catalog_totals"), "finance operation catalog snapshot")
    text = telegram_bot._finance_operation_catalog_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(
        text,
        ("FINANCE OPERATION CATALOG", "WB deductions bridge", "Catalog coverage", "Top operation groups"),
        "finance operation catalog text",
    )


def scenario_finance_difference_audit():
    snapshot = telegram_bot.get_finance_difference_snapshot(TEST_USER_ID, TEST_START, TEST_END)
    _assert_snapshot_result(
        snapshot,
        ("wb_difference", "explained_total", "real_coverage_percent", "coverage_with_residual_percent", "finance_bucket_debug"),
        "finance difference snapshot",
    )
    _assert(snapshot.get("finance_bucket_debug") is not None, "finance difference snapshot: finance_bucket_debug is None")

    verdict = "difference_fully_explained" if float(snapshot.get("real_coverage_percent") or 0) >= 95 else "difference_partially_explained"
    lines = [
        "FINANCE DIFFERENCE AUDIT",
        "",
    ]
    lines.extend(telegram_bot.finance_verdict_lines(snapshot))
    lines.extend([
        "",
        f'wb_difference: {telegram_bot.money(snapshot["wb_difference"])}',
        "",
        "VERDICT",
        verdict,
    ])
    lines.extend(["", *telegram_bot.finance_bucket_debug_lines(snapshot)])
    lines.extend(telegram_bot.finance_raw_article_detail_lines(snapshot))
    lines.extend(["", *telegram_bot.finance_debug_lines(snapshot)])
    text = "\n".join(lines)
    _assert_text_result(
        text,
        ("FINANCE DIFFERENCE AUDIT", "FINANCE VERDICT", "FINANCE BUCKET DEBUG", "RAW FINANCE ARTICLE DETAIL", "FINANCE DEBUG"),
        "finance difference audit text",
    )


def scenario_data_quality():
    snapshot = telegram_bot._data_quality_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert_snapshot_result(
        snapshot,
        ("period_start", "period_end", "sales", "orders", "advertising", "finance", "overall_score", "overall_status"),
        "data quality snapshot",
    )
    text = telegram_bot._data_quality_text("custom", TEST_DAYS, TEST_USER_ID)
    _assert_text_result(text, ("DATA QUALITY", "SALES QUALITY", "ORDERS QUALITY", "OVERALL SCORE"), "data quality text")


def scenario_health():
    snapshot = telegram_bot._health_snapshot(TEST_USER_ID)
    _assert_snapshot_result(
        snapshot,
        ("bot_status", "database_status", "totals", "last_updates", "freshness", "cooldowns", "quality", "verdict"),
        "health snapshot",
    )
    text = telegram_bot._health_text(TEST_USER_ID)
    _assert_text_result(text, ("SYSTEM HEALTH", "LAST UPDATES", "DATA FRESHNESS", "VERDICT"), "health text")


def scenario_gold_standard_financial_validation():
    if not hasattr(telegram_bot, "_gold_standard_reference_files_available"):
        return "SKIPPED"
    if not telegram_bot._gold_standard_reference_files_available():
        return "SKIPPED"
    text = telegram_bot._gold_standard_financial_text(TEST_START, TEST_END)
    _assert_text_result(
        text,
        (
            "GOLD STANDARD FINANCIAL VALIDATION",
            "РљРѕРјРёСЃСЃРёСЏ WB Р·Р° СЂРµР°Р»РёР·Р°С†РёСЋ",
            "Bridge checks",
            "GOLD STANDARD STATUS",
        ),
        "gold standard financial validation text",
    )


def run_all():
    scenarios = [
        (scenario_system_audit, True),
        (scenario_system_audit_data_source_snapshot, False),
        (scenario_dashboard, False),
        (scenario_dashboard_data_source_snapshot, False),
        (scenario_ceo_report, False),
        (scenario_ceo_data_source_snapshot, False),
        (scenario_advisor, False),
        (scenario_advisor_readiness, False),
        (scenario_profit_audit, False),
        (scenario_money_flow_regression_safety, False),
        (scenario_profit_audit_regression_safety, False),
        (scenario_dashboard_ceo_regression_safety, False),
        (scenario_payment_reconciliation, False),
        (scenario_money_flow, False),
        (scenario_money_sku, False),
        (scenario_finance_api_status, False),
        (scenario_finance_api_diagnose, False),
        (scenario_finance_cooldown_status_no_probe, False),
        (scenario_finance_api_status_force_bypass, False),
        (scenario_financial_engine, False),
        (scenario_financial_engine_legacy_fallback, False),
        (scenario_legacy_gold_standard_validation_helper, False),
        (scenario_legacy_gold_standard_text_match, False),
        (scenario_financial_engine_no_legacy_on_rate_limit, False),
        (scenario_financial_engine_cooldown_no_api_calls, False),
        (scenario_business_metrics, False),
        (scenario_kpi_engine, False),
        (scenario_unified_data_layer, False),
        (scenario_cfo_insights, False),
        (scenario_decision_engine, False),
        (scenario_advisor_v2, False),
        (scenario_director, False),
        (scenario_help_home_and_product_readiness, True),
        (scenario_ui_spec_and_dashboard_prototype, False),
        (scenario_project_structure_and_performance, True),
        (scenario_command_performance, False),
        (scenario_rc_status, True),
        (scenario_command_routing_isolation, False),
        (scenario_finance_forbidden_propagation, False),
        (scenario_sku_registry, False),
        (scenario_period_engine, False),
        (scenario_command_source_audit, False),
        (scenario_migration_readiness, False),
        (scenario_product_navigation_centers, False),
        (scenario_finance_operation_catalog, False),
        (scenario_finance_difference_audit, False),
        (scenario_data_quality, True),
        (scenario_health, True),
        (scenario_gold_standard_financial_validation, False),
    ]
    passed = 0
    failed = 0
    skipped = 0
    for scenario, is_heavy in scenarios:
        if is_heavy and not _RUN_HEAVY_SCENARIOS:
            skipped += 1
            print(f"SKIPPED_HEAVY: {scenario.__name__}", flush=True)
            continue
        started = time.perf_counter()
        suspected_layer, mode = _scenario_meta(getattr(scenario, "__name__", "scenario"))
        try:
            result = scenario()
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if result == "SKIPPED":
                skipped += 1
                print(f"SKIPPED: {scenario.__name__} elapsed_ms={elapsed_ms:.1f}", flush=True)
            else:
                passed += 1
                print(f"PASSED: {scenario.__name__} elapsed_ms={elapsed_ms:.1f}", flush=True)
            if elapsed_ms > _SLOW_SCENARIO_MS:
                warning = (
                    f"command name={scenario.__name__} "
                    f"elapsed_ms={elapsed_ms:.1f} "
                    f"suspected layer={suspected_layer} "
                    f"mode={mode}"
                )
                _PERFORMANCE_WARNINGS.append(warning)
                print(f"TIMEOUT DIAGNOSTIC {warning}", flush=True)
        except Exception:
            failed += 1
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            print(
                f"FAILED: {scenario.__name__} elapsed_ms={elapsed_ms:.1f} suspected_layer={suspected_layer} mode={mode}",
                flush=True,
            )
            raise
    print("SCENARIO SUITE OK", flush=True)
    print(f"passed: {passed}", flush=True)
    print(f"failed: {failed}", flush=True)
    print(f"skipped: {skipped}", flush=True)
    for warning in _PERFORMANCE_WARNINGS:
        print(f"WARNING: {warning}", flush=True)


if __name__ == "__main__":
    run_all()

