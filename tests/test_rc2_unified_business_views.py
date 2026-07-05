from __future__ import annotations

import asyncio
from pathlib import Path
import re
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
import vooglii_telegram.legacy_bot as legacy_bot
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


FORBIDDEN_CUSTOMER_TOKENS = [
    "Finance API",
    "KPI Engine",
    "CFO Insights",
    "Decision Engine",
    "UDL",
    "raw exception",
    "Не удалось открыть",
    "last_30_days",
    "current_month",
    "Себестоимость: 0.00",
]


class _Message:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _User:
    def __init__(self, user_id: int = 100, username: str = "owner_user"):
        self.id = user_id
        self.username = username


class _Update:
    def __init__(self, text: str = "", user_id: int = 100, username: str = "owner_user"):
        self.effective_user = _User(user_id, username)
        self.message = _Message(text)


class _Context:
    def __init__(self, args=None):
        self.args = list(args or [])
        self.bot = SimpleNamespace()
        self.application = None


def _run(coro):
    return asyncio.run(coro)


def _period_line(text: str) -> str:
    match = re.search(r"^Период:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _assert_customer_safe(text: str):
    for token in FORBIDDEN_CUSTOMER_TOKENS:
        assert token not in text, f"forbidden token leaked into customer output: {token}"


def _patch_rc2_sources(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda _user_id: "owner")
    monkeypatch.setattr(legacy_bot, "get_user_role", telegram_bot.get_user_role)
    monkeypatch.setattr(
        telegram_bot,
        "get_user",
        lambda _user_id: (1, "owner_user", "token", "PRO", None, None, None, "owner", None),
    )
    monkeypatch.setattr(legacy_bot, "get_user", telegram_bot.get_user)
    monkeypatch.setattr(
        telegram_bot,
        "_health_snapshot",
        lambda _user: {
            "bot_status": "OK",
            "database_status": "OK",
            "quality": {"sales": {"status": "OK"}, "advertising": {"status": "OK"}},
            "last_updates": {"sales": "2026-07-05 10:30:00"},
        },
    )
    monkeypatch.setattr(legacy_bot, "_health_snapshot", telegram_bot._health_snapshot)
    monkeypatch.setattr(telegram_bot, "_product_readiness_snapshot", lambda user=None, **kwargs: {"product_status": "READY", "remaining_blockers": []})
    monkeypatch.setattr(legacy_bot, "_product_readiness_snapshot", telegram_bot._product_readiness_snapshot)
    monkeypatch.setattr(telegram_bot, "_project_structure_readiness_snapshot", lambda user=None, days=None, **kwargs: {"status": "READY"})
    monkeypatch.setattr(legacy_bot, "_project_structure_readiness_snapshot", telegram_bot._project_structure_readiness_snapshot)
    monkeypatch.setattr(telegram_bot, "_sku_registry_snapshot", lambda _user, _days, **kwargs: {"registry_status": "READY", "coverage_percent": 100.0, "known_skus": list(range(14)), "missing_skus": []})
    monkeypatch.setattr(legacy_bot, "_sku_registry_snapshot", telegram_bot._sku_registry_snapshot)
    monkeypatch.setattr(telegram_bot, "get_stock_forecast", lambda _user, _a, _b: [])
    monkeypatch.setattr(legacy_bot, "get_stock_forecast", telegram_bot.get_stock_forecast)
    monkeypatch.setattr(telegram_bot, "_stock_snapshot_date", lambda _user: "2026-07-05")
    monkeypatch.setattr(legacy_bot, "_stock_snapshot_date", telegram_bot._stock_snapshot_date)

    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "WAITING"})
    monkeypatch.setattr(legacy_bot, "_finance_api_status_snapshot", telegram_bot._finance_api_status_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, _days, context=None, **kwargs: {
            "revenue": 120000.0,
            "payout": 91000.0,
            "cost_price": 0.0,
            "advertising": 29900.63,
            "logistics": 0.0,
            "storage": 0.0,
            "other": 0.0,
            "acquiring": 0.0,
            "deductions": 0.0,
            "unexplained": 0.0,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
        },
    )
    monkeypatch.setattr(legacy_bot, "_report_mgmt_snapshot", telegram_bot._report_mgmt_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None, **kwargs: {
            "official_new_finance_available": False,
            "official_net_profit": None,
            "status": "OFFICIAL_NEW_FINANCE_UNAVAILABLE",
            "warnings": [],
        },
    )
    monkeypatch.setattr(legacy_bot, "_financial_engine_snapshot", telegram_bot._financial_engine_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None, **kwargs: {
            "weekly_payout_total_all": 70000.0,
            "sales_for_pay_total": 91000.0,
            "status": "OK",
        },
    )
    monkeypatch.setattr(legacy_bot, "_payment_reconciliation_snapshot", telegram_bot._payment_reconciliation_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None, **kwargs: {
            "coverage_percent": 0.0,
            "status": "WAITING_WB",
        },
    )
    monkeypatch.setattr(legacy_bot, "get_finance_difference_snapshot", telegram_bot.get_finance_difference_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days, **kwargs: {
            "normalized_status": "ADS_PARTIAL",
            "status_kind": "error",
            "raw_status": "ADS_PARTIAL_MISSING_IDS",
            "last_success": "2026-07-05 09:00:00",
            "total_spend": 29900.63,
            "linked_spend": 26000.0,
            "unlinked_spend": 3900.63,
            "linkability_percent": 86.9,
            "campaigns_total": 10,
            "campaigns_linked": 8,
            "campaigns_unlinked": 2,
            "status": "MEDIUM",
            "delta": 1663.27,
        },
    )
    monkeypatch.setattr(legacy_bot, "_advertising_customer_snapshot", telegram_bot._advertising_customer_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_data_quality_snapshot",
        lambda _user, _days, context=None, **kwargs: {"overall_status": "HIGH", "sales": {"status": "OK"}, "advertising": {"status": "OK"}},
    )
    monkeypatch.setattr(legacy_bot, "_data_quality_snapshot", telegram_bot._data_quality_snapshot)
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (18, 135000.0, 2, 7000.0))
    monkeypatch.setattr(legacy_bot, "get_orders_stats", telegram_bot.get_orders_stats)
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (14, 120000.0))
    monkeypatch.setattr(legacy_bot, "get_period_stats", telegram_bot.get_period_stats)
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats",
        lambda _days, _user: (120000.0, 3000.0, 91000.0, 0.0, 0.0, 29900.63, 0.0, 0.0, 29900.63, 0.0, None, 0.0, 3),
    )
    monkeypatch.setattr(legacy_bot, "get_profit_stats", telegram_bot.get_profit_stats)
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats_after_tax",
        lambda _days, _user: {
            "profit_before_tax": None,
            "tax": 0.0,
            "profit_after_tax": 0.0,
            "margin_after_tax": 0.0,
            "tax_notes": [],
            "tax_configured": False,
        },
    )
    monkeypatch.setattr(legacy_bot, "get_profit_stats_after_tax", telegram_bot.get_profit_stats_after_tax)
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "business_health": "WARNING",
            "business_state": {"sales": "GOOD", "finance": "BLOCKED", "ads": "GOOD"},
            "main_recommendation": "Не закрывать месяц, пока WB не подтвердит финансовые данные.",
            "main_recommendation_action": "Открыть /finance и сверить деньги.",
            "today_actions": ["Открыть /advisor."],
            "risks": ["Финансовые данные WB ещё не подтверждены."],
            "advertising": telegram_bot._advertising_customer_snapshot(user, days),
            "products": telegram_bot._products_center_snapshot(user, days),
            "unified_finance": build_unified_financial_snapshot_dict(user, days, bot=telegram_bot),
        },
    )
    monkeypatch.setattr(legacy_bot, "_business_center_snapshot", telegram_bot._business_center_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_advisor_v2_text",
        lambda *_args, **_kwargs: "Finance API | KPI Engine | CFO Insights | Decision Engine | UDL",
    )
    monkeypatch.setattr(legacy_bot, "_advisor_v2_text", telegram_bot._advisor_v2_text)


def test_rc2_unified_business_views_runtime(monkeypatch):
    _patch_rc2_sources(monkeypatch)
    handlers = telegram_bot._command_handlers()
    outputs: dict[str, str] = {}

    commands = ("business", "finance", "pnl", "report", "dashboard", "ceo", "advisor", "system", "products")
    for command in commands:
        update = _Update(f"/{command}")
        _run(handlers[command](update, _Context()))
        outputs[command] = update.message.replies[-1]
        _assert_customer_safe(outputs[command])

    period_outputs = {name: _period_line(outputs[name]) for name in ("business", "finance", "pnl", "report", "dashboard", "ceo", "advisor")}
    unique_periods = {value for value in period_outputs.values() if value}
    assert len(unique_periods) == 1, period_outputs

    for command in ("business", "finance", "pnl", "report", "dashboard", "ceo"):
        assert "29 900.63" in outputs[command], command

    assert "120 000.00" in outputs["pnl"]
    assert "120 000.00" in outputs["report"]
    assert "120 000.00" in outputs["dashboard"]
    assert "120 000.00" in outputs["ceo"]

    assert "Финансовые данные WB" in outputs["finance"]
    assert "Финансовые данные WB" in outputs["advisor"]
    assert "ожидают подтверждения" in outputs["system"] or "ещё не подтверждены" in outputs["advisor"]

    assert "Себестоимость: заполнена, ждёт расчёта по продажам" in outputs["finance"]
    assert "Себестоимость: заполнена, ждёт расчёта по продажам" in outputs["pnl"]
    assert "Себестоимость: заполнена, ждёт расчёта по продажам" in outputs["report"]
    assert "Себестоимость: заполнена, ждёт расчёта по продажам" in outputs["dashboard"]
    assert "Себестоимость: заполнена, ждёт расчёта по продажам" in outputs["ceo"]
    assert "Себестоимость заполнена, расчёт по продажам появится после следующего обновления." in outputs["products"]
