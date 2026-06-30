"""Minimal readonly smoke checks for the VOOGLII project.

This script avoids Telegram polling, WB API calls, and DB writes.
Run with:
    python tests/smoke_readonly.py
"""

from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
from wb_agent import finance_debug, formatting, health_debug
from wb_agent.ui_spec import build_dashboard_prototype_snapshot, build_ui_spec_snapshot

TEST_USER_ID = 658486226
TEST_START = "2026-05-01"
TEST_END = "2026-05-31"
TEST_DAYS = (TEST_START, TEST_END)
_FIXTURE_CACHE = {}
_PERFORMANCE_WARNINGS = []
_SLOW_STEP_MS = 10000.0


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _cached(name, builder):
    if name not in _FIXTURE_CACHE:
        _FIXTURE_CACHE[name] = builder()
    value = _FIXTURE_CACHE[name]
    return dict(value) if isinstance(value, dict) else value


def _timed_step(name, fn, suspected_layer="generic", mode="readonly"):
    started = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if elapsed_ms > _SLOW_STEP_MS:
        warning = f"command name={name} elapsed_ms={elapsed_ms:.1f} suspected layer={suspected_layer} mode={mode}"
        _PERFORMANCE_WARNINGS.append(warning)
        print(f"TIMEOUT DIAGNOSTIC {warning}", flush=True)
    else:
        print(f"STEP OK name={name} elapsed_ms={elapsed_ms:.1f} layer={suspected_layer} mode={mode}", flush=True)
    return result


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

    telegram_bot.asyncio.run(_invoke())
    return outputs, replies


def finance_snapshot_for_health():
    return {
        "status": "HIGH",
        "real_coverage_percent": 73.8,
        "coverage_with_residual_percent": 100.0,
        "wb_difference": 299404.94,
        "residual_other_deductions": 78491.53,
        "finance_double_count_risk": True,
        "finance_double_count_risk_sources": ["deductions"],
        "finance_confirmed_double_count_risk": True,
        "finance_possible_double_count_risk": True,
        "finance_double_count_risk_reason": "raw overlapping components present in wb_difference",
        "explained_total": 299404.94,
        "finance_components_total": 220913.41,
        "explained_vs_difference_delta": 0.0,
        "wb_difference_abs": 299404.94,
        "is_overexplained": False,
        "overexplained_amount": 0.0,
        "finance_residual_debug": {
            "residual_other_deductions": 78491.53,
            "residual_source_type": "calculated",
            "residual_formula": "max(0, ...)",
            "residual_abs": 78491.53,
            "residual_share_of_wb_difference_percent": 26.2,
            "residual_share_of_unexplained_percent": 100.0,
            "residual_is_balancing_item": "yes",
            "residual_can_double_count": "yes",
            "residual_confidence": "HIGH",
        },
    }


def check_core_imports():
    _assert(formatting is not None, "wb_agent.formatting import failed")
    _assert(finance_debug is not None, "wb_agent.finance_debug import failed")
    _assert(health_debug is not None, "wb_agent.health_debug import failed")


def check_core_functions():
    for name in (
        "get_finance_difference_snapshot",
        "_data_quality_snapshot",
        "_health_snapshot",
        "_system_audit_snapshot",
        "_director_text",
        "_business_metrics_text",
        "_unified_data_text",
    ):
        _assert(hasattr(telegram_bot, name), f"telegram_bot missing {name}")
        _assert(callable(getattr(telegram_bot, name)), f"telegram_bot {name} is not callable")


def check_light_snapshots():
    snapshot_cases = [
        ("finance_difference", lambda: telegram_bot.get_finance_difference_snapshot(TEST_USER_ID, TEST_START, TEST_END), ("wb_difference", "explained_total")),
        ("data_quality", lambda: telegram_bot._data_quality_snapshot(TEST_USER_ID, TEST_DAYS), ("sales", "orders", "advertising", "finance")),
        ("health", lambda: telegram_bot._health_snapshot(TEST_USER_ID), ("database_status", "quality", "verdict")),
        ("system_audit", lambda: telegram_bot._system_audit_snapshot(TEST_USER_ID), ("health", "quality", "verdict")),
    ]
    for cache_name, builder, keys in snapshot_cases:
        snapshot = _cached(cache_name, builder)
        _assert(isinstance(snapshot, dict), f"{cache_name} should return dict")
        for key in keys:
            _assert(key in snapshot, f"{cache_name} missing {key}")


def check_light_texts():
    text_cases = [
        ("director_text", lambda: telegram_bot._director_text(TEST_USER_ID, TEST_DAYS), "VOOGLII DIRECTOR"),
        ("product_readiness_text", lambda: telegram_bot._product_readiness_text(TEST_USER_ID), "PRODUCT READINESS"),
        ("telegram_identity_text", telegram_bot._telegram_identity_text, "TELEGRAM IDENTITY"),
        ("ui_spec_text", telegram_bot._ui_spec_text, "VOOGLII UI SPECIFICATION v1.0"),
        ("dashboard_prototype_text", lambda: telegram_bot._dashboard_prototype_text(TEST_USER_ID, TEST_DAYS), "VOOGLII DASHBOARD PROTOTYPE"),
        ("udl_text", lambda: telegram_bot._unified_data_text(TEST_START, TEST_END, TEST_USER_ID), "UNIFIED DATA LAYER"),
        ("business_metrics_text", lambda: telegram_bot._business_metrics_text(TEST_START, TEST_END, TEST_USER_ID), "BUSINESS METRICS"),
        ("sku_registry_text", lambda: telegram_bot._sku_registry_text(TEST_USER_ID, TEST_DAYS), "SKU REGISTRY"),
        ("system_audit_text", lambda: telegram_bot._system_audit_text(TEST_USER_ID), "SYSTEM"),
        ("health_text", lambda: telegram_bot._health_text(TEST_USER_ID), "HEALTH"),
        ("data_quality_text", lambda: telegram_bot._data_quality_text("custom", TEST_DAYS, TEST_USER_ID), "DATA QUALITY"),
        ("period_engine_text", lambda: telegram_bot._period_engine_text(args=[TEST_START, TEST_END], today="2026-06-26"), "PERIOD ENGINE"),
    ]
    for cache_name, builder, marker in text_cases:
        text = _cached(cache_name, builder)
        _assert(isinstance(text, str), f"{cache_name} should return str")
        _assert(bool(text.strip()), f"{cache_name} should not be empty")
        _assert(marker in text, f"{cache_name} missing marker {marker}")


def check_period_engine_helpers():
    month_snapshot = telegram_bot._period_engine_snapshot(args=["2026-05-01", "2026-05-31"], today="2026-06-26")
    _assert(str(month_snapshot.get("period_type") or "") == "MONTH", "2026-05-01..2026-05-31 should be MONTH")
    previous_month_snapshot = telegram_bot._period_engine_snapshot(args=["previous_month"], today="2026-06-26")
    _assert(previous_month_snapshot.get("start_date") == "2026-05-01", "previous_month start_date mismatch")
    _assert(previous_month_snapshot.get("end_date") == "2026-05-31", "previous_month end_date mismatch")


def check_home_and_legacy_routes():
    ui_outputs, ui_replies = _run_handler(telegram_bot.ui_command, "/ui spec", ["spec"])
    _assert(not ui_replies, "ui spec should not fall back to reply_text help")
    _assert(len(ui_outputs) == 1 and "VOOGLII UI SPECIFICATION" in ui_outputs[0], "ui spec should render specification text")

    telegram_outputs, telegram_replies = _run_handler(telegram_bot.telegram_command, "/telegram identity", ["identity"])
    _assert(not telegram_replies, "telegram identity should not fall back to reply_text help")
    _assert(len(telegram_outputs) == 1 and "TELEGRAM IDENTITY" in telegram_outputs[0], "telegram identity should render identity text")

    dashboard_prototype_outputs, dashboard_prototype_replies = _run_handler(telegram_bot.dashboard_command, "/dashboard prototype", ["prototype"])
    _assert(not dashboard_prototype_replies, "dashboard prototype should not fall back to reply_text help")
    _assert(len(dashboard_prototype_outputs) == 1 and "VOOGLII DASHBOARD PROTOTYPE" in dashboard_prototype_outputs[0], "dashboard prototype should render prototype text")

    outputs, replies = _run_handler(telegram_bot.director_command, "/director current_month", ["current_month"])
    _assert(not replies, "director current_month should not fall back to reply_text help")
    _assert(len(outputs) == 1 and "VOOGLII DIRECTOR" in outputs[0], "director current_month should render VOOGLII DIRECTOR")

    original_diagnose_text = telegram_bot._finance_api_diagnose_text
    try:
        telegram_bot._finance_api_diagnose_text = lambda user: "FINANCE API DIAGNOSE\n\nSUMMARY\nFinance API available."
        diagnose_outputs, diagnose_replies = _run_handler(telegram_bot.finance_command, "/finance api diagnose", ["api", "diagnose"])
    finally:
        telegram_bot._finance_api_diagnose_text = original_diagnose_text
    _assert(not diagnose_replies, "finance api diagnose should not fall back to reply_text help")
    _assert(len(diagnose_outputs) == 1 and "FINANCE API DIAGNOSE" in diagnose_outputs[0], "finance api diagnose should render FINANCE API DIAGNOSE")

    system_audit_outputs, system_audit_replies = _run_handler(telegram_bot.system_command, "/system audit", ["audit"])
    _assert(not system_audit_replies, "system audit should keep legacy route")
    _assert(len(system_audit_outputs) == 1, "system audit should produce exactly one output")
    _assert(any(marker in system_audit_outputs[0] for marker in ("SYSTEM", "DATABASE", "DATA QUALITY")), "system audit should render legacy system audit output")


def check_product_navigation_routes():
    help_outputs, help_replies = _run_handler(telegram_bot.menu_command, "/help", [])
    _assert(not help_outputs, "help should use reply_text")
    _assert(len(help_replies) == 1, "help should render one reply_text message")
    help_text = help_replies[0]
    _assert("/home" in help_text, "help should contain /home")
    _assert("/business" in help_text, "help should contain /business")
    _assert("/finance" in help_text, "help should contain /finance")
    _assert("/help developer" in help_text, "help should contain /help developer")
    _assert("/udl" not in help_text and "/command audit" not in help_text, "regular help should not expose engineering commands")

    developer_outputs, developer_replies = _run_handler(telegram_bot.menu_command, "/help developer", ["developer"])
    _assert(not developer_outputs, "help developer should use reply_text")
    _assert(len(developer_replies) == 1, "help developer should render one reply_text message")
    developer_text = developer_replies[0]
    _assert("DEVELOPER HELP" in developer_text, "help developer should render developer help title")
    _assert("/ui spec" in developer_text, "help developer should contain /ui spec")
    _assert("/dashboard prototype" in developer_text, "help developer should contain /dashboard prototype")
    _assert("/telegram identity" in developer_text, "help developer should contain /telegram identity")
    _assert("/udl" in developer_text, "help developer should contain /udl")
    _assert("/command audit" in developer_text, "help developer should contain /command audit")

    route_cases = [
        ("business_center", telegram_bot.business_command, "/business", [], "VOOGLII BUSINESS", "product-mode"),
        ("business_center_month", telegram_bot.business_command, "/business current_month", ["current_month"], "VOOGLII BUSINESS", "product-mode"),
        ("business_metrics_legacy", telegram_bot.business_command, "/business metrics current_month", ["metrics", "current_month"], "BUSINESS METRICS", "legacy-mode"),
        ("finance_center", telegram_bot.finance_command, "/finance", [], "VOOGLII FINANCE", "product-mode"),
        ("finance_center_month", telegram_bot.finance_command, "/finance current_month", ["current_month"], "VOOGLII FINANCE", "product-mode"),
        ("finance_api_status_legacy", telegram_bot.finance_command, "/finance api status", ["api", "status"], "FINANCE API STATUS", "legacy-mode"),
        ("products_center", telegram_bot.products_command, "/products", [], "VOOGLII PRODUCTS", "product-mode"),
        ("analytics_center", telegram_bot.analytics_command, "/analytics", [], "VOOGLII ANALYTICS", "product-mode"),
        ("system_center", telegram_bot.system_command, "/system", [], "VOOGLII SYSTEM", "product-mode"),
        ("ui_spec", telegram_bot.ui_command, "/ui spec", ["spec"], "VOOGLII UI SPECIFICATION", "readonly"),
        ("telegram_identity", telegram_bot.telegram_command, "/telegram identity", ["identity"], "TELEGRAM IDENTITY", "readonly"),
        ("dashboard_prototype", telegram_bot.dashboard_command, "/dashboard prototype", ["prototype"], "VOOGLII DASHBOARD PROTOTYPE", "readonly"),
    ]
    for case_name, handler, command_text, args, marker, mode in route_cases:
        outputs, replies = _run_handler(handler, command_text, args)
        _assert(not replies, f"{case_name} should not fall back to reply_text help")
        _assert(len(outputs) == 1 and marker in outputs[0], f"{case_name} should render {marker}")


def check_ui_spec_module():
    ui_snapshot = build_ui_spec_snapshot()
    _assert(isinstance(ui_snapshot, dict), "build_ui_spec_snapshot should return dict")
    _assert(str(ui_snapshot.get("status") or "") == "READY", "ui spec status should be READY")
    _assert(str(ui_snapshot.get("product") or "") == "VOOGLII", "ui spec product should be VOOGLII")
    dashboard_snapshot = build_dashboard_prototype_snapshot()
    _assert(isinstance(dashboard_snapshot, dict), "build_dashboard_prototype_snapshot should return dict")
    _assert(str(dashboard_snapshot.get("screen") or "") == "dashboard_prototype", "dashboard prototype screen mismatch")


def check_formatting_helpers():
    _assert(isinstance(formatting.money(123.45), str), "money() should return str")
    _assert(isinstance(formatting.format_seconds(125), str), "format_seconds() should return str")
    _assert(isinstance(formatting._ads_percent_text(12.3), str), "_ads_percent_text() should return str")
    _assert(isinstance(formatting._ads_number_text(12.3), str), "_ads_number_text() should return str")


def check_finance_debug_helpers():
    finance_snapshot = {
        "coverage_with_residual_percent": 100.0,
        "real_coverage_percent": 73.8,
        "is_overexplained": False,
        "finance_confirmed_double_count_risk": True,
        "finance_possible_double_count_risk": True,
        "finance_confirmed_double_count_risk_sources": ["deductions"],
        "finance_double_count_risk_reason": "raw overlapping components present in wb_difference",
        "finance_double_count_risk": True,
        "finance_double_count_risk_sources": ["deductions", "residual_other_deductions"],
        "wb_difference": 299404.94,
        "explained_total": 299404.94,
        "finance_components_total": 220913.41,
        "explained_vs_difference_delta": 0.0,
        "wb_difference_abs": 299404.94,
        "overexplained_amount": 0.0,
        "residual_other_deductions": 78491.53,
        "finance_residual_debug": {
            "residual_other_deductions": 78491.53,
            "residual_source_type": "calculated",
            "residual_formula": "max(0, ...)",
            "residual_abs": 78491.53,
            "residual_share_of_wb_difference_percent": 26.2,
            "residual_share_of_unexplained_percent": 100.0,
            "residual_is_balancing_item": "yes",
            "residual_can_double_count": "yes",
            "residual_confidence": "HIGH",
        },
        "finance_bucket_debug": {
            "deductions": {
                "total_amount": 76736.0,
                "rows_count": 2,
                "articles": ["deduction"],
            },
        },
        "finance_raw_article_debug": {"rows": []},
    }
    for helper in (
        finance_debug.finance_verdict_lines,
        finance_debug.finance_bucket_debug_lines,
        finance_debug.finance_raw_article_detail_lines,
        finance_debug.finance_debug_lines,
    ):
        result = helper(finance_snapshot)
        _assert(isinstance(result, list), f"{helper.__name__} should return list")
        _assert(all(isinstance(item, str) for item in result), f"{helper.__name__} should return list[str]")


def check_health_debug_helpers():
    health_snapshot = {
        "period_start": "2026-05-01",
        "period_end": "2026-05-31",
        "sales": {"status": "HIGH"},
        "orders": {"status": "HIGH"},
        "advertising": {"status": "HIGH"},
        "finance": {"status": "HIGH"},
        "overall_score": 100.0,
        "overall_status": "HIGH",
        "recommendation": "ok",
        "bot_status": "OK",
        "database_status": "OK",
        "database_exists": "yes",
        "totals": {"sales": 10},
        "last_updates": {"sales": "2026-05-31"},
        "freshness": {"sales": "fresh"},
        "cooldowns": {"statistics": {"retry_after": "unknown"}},
        "quality": {"overall_score": 100.0, "overall_status": "HIGH"},
        "verdict": "system_ok",
        "health": {"database_status": "OK"},
        "ads_health": {"status": "HIGH", "linkability_percent": 100.0},
        "finance_health": finance_snapshot_for_health(),
        "cache": {"sales": {"atomic_write": "yes"}},
        "write_safety": {"sales applyhistorical": {"guard": "yes"}},
    }
    for helper in (
        health_debug.data_quality_lines,
        health_debug.health_lines,
        health_debug.system_audit_lines,
    ):
        result = helper(health_snapshot)
        _assert(isinstance(result, list), f"{helper.__name__} should return list")
        _assert(all(isinstance(item, str) for item in result), f"{helper.__name__} should return list[str]")


def run_all():
    steps = [
        ("core_imports", check_core_imports, "imports", "readonly"),
        ("core_functions", check_core_functions, "imports", "readonly"),
        ("light_snapshots", check_light_snapshots, "snapshots", "readonly"),
        ("light_texts", check_light_texts, "renderers", "readonly"),
        ("period_engine_helpers", check_period_engine_helpers, "period", "readonly"),
        ("home_and_legacy_routes", check_home_and_legacy_routes, "router", "legacy-mode"),
        ("product_navigation_routes", check_product_navigation_routes, "router", "product-mode"),
        ("ui_spec_module", check_ui_spec_module, "ui-spec", "readonly"),
        ("formatting_helpers", check_formatting_helpers, "formatting", "readonly"),
        ("finance_debug_helpers", check_finance_debug_helpers, "finance-debug", "readonly"),
        ("health_debug_helpers", check_health_debug_helpers, "health-debug", "readonly"),
    ]
    for name, fn, suspected_layer, mode in steps:
        _timed_step(name, fn, suspected_layer=suspected_layer, mode=mode)


if __name__ == "__main__":
    run_all()
    print("SMOKE READONLY OK", flush=True)
    for warning in _PERFORMANCE_WARNINGS:
        print(f"WARNING: {warning}", flush=True)
