from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
import vooglii_telegram.legacy_bot as legacy_bot
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict
from vooglii_telegram.ux.status_labels import (
    ADS_PARTIAL,
    COST_READY_PENDING_CALC,
    FINANCE_PARTIAL,
    SALES_OK,
)


FORBIDDEN_VARIANTS = [
    "частично готово",
    "частично доступны",
    "ожидает данные WB",
    "SUCCESS",
    "FAILED",
    "UNKNOWN",
    "NOT_ACTIVE",
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


def _patch_sources(monkeypatch):
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
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: (1, "owner_user", "token", "PRO", None, None, None, "owner", None))
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
    monkeypatch.setattr(telegram_bot, "_sku_registry_snapshot", lambda _user, _days, **kwargs: {"registry_status": "READY", "coverage_percent": 100.0, "known_skus": list(range(14)), "missing_skus": [], "critical_stock_count": 3})
    monkeypatch.setattr(legacy_bot, "_sku_registry_snapshot", telegram_bot._sku_registry_snapshot)
    monkeypatch.setattr(telegram_bot, "get_stock_forecast", lambda _user, _a, _b: [{"article": "SKU-1", "risk_level": "critical", "days_left": 2}])
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
            "coverage_percent": 42.0,
            "status": "PARTIAL",
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
    monkeypatch.setattr(telegram_bot, "get_profit_stats", lambda _days, _user: (120000.0, 3000.0, 91000.0, 0.0, 0.0, 29900.63, 0.0, 0.0, 29900.63, 0.0, None, 0.0, 3))
    monkeypatch.setattr(legacy_bot, "get_profit_stats", telegram_bot.get_profit_stats)
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats_after_tax",
        lambda _days, _user: {"profit_before_tax": None, "tax": 0.0, "profit_after_tax": 0.0, "margin_after_tax": 0.0, "tax_notes": [], "tax_configured": False},
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
            "risks": ["Финансовые данные WB подтверждены частично."],
            "advertising": telegram_bot._advertising_customer_snapshot(user, days),
            "products": telegram_bot._products_center_snapshot(user, days),
            "unified_finance": build_unified_financial_snapshot_dict(user, days, bot=telegram_bot),
        },
    )
    monkeypatch.setattr(legacy_bot, "_business_center_snapshot", telegram_bot._business_center_snapshot)


def test_rc3_customer_status_labels_are_consistent(monkeypatch):
    _patch_sources(monkeypatch)
    monkeypatch.setattr(
        telegram_bot,
        "_home_snapshot",
        lambda user=100, days=("2026-07-01", "2026-07-31"): {
            "status": "OK",
            "period_label": "Июль 2026",
            "sales_status": "OK",
            "finance_status": "FINANCE_PARTIAL",
            "ads_status": "ADS_PARTIAL",
            "costs_status": "COST_OK",
            "cost_value": None,
            "cost_coverage_percent": 100.0,
            "wb_connected": True,
            "last_updates": {"sales": "2026-07-05 10:30:00"},
        },
    )
    handlers = telegram_bot._command_handlers()
    outputs: dict[str, str] = {}

    for command in ("home", "business", "finance", "pnl", "report", "dashboard", "ceo", "advisor", "system", "products"):
        update = _Update(f"/{command}")
        _run(handlers[command](update, _Context()))
        outputs[command] = update.message.replies[-1]

    for text in outputs.values():
        for token in FORBIDDEN_VARIANTS:
            assert token not in text, token

    for command in ("home", "finance", "report", "dashboard", "ceo", "advisor", "system"):
        assert FINANCE_PARTIAL in outputs[command], command

    for command in ("home", "business", "system"):
        assert SALES_OK in outputs[command], command

    for command in ("business", "advisor", "report", "dashboard", "system"):
        assert ADS_PARTIAL in outputs[command], command

    for command in ("home", "business", "finance", "pnl", "report", "dashboard", "ceo", "advisor", "products"):
        assert COST_READY_PENDING_CALC in outputs[command], command
