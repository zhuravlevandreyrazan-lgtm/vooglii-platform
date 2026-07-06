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

from vooglii_finance.unified_snapshot import build_consistency_audit, build_unified_financial_snapshot_dict


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
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: (1, "owner_user", "token", "PRO", None, None, None, "owner", None))
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda _user_id: "owner")
    monkeypatch.setattr(legacy_bot, "get_user", telegram_bot.get_user)
    monkeypatch.setattr(legacy_bot, "get_user_role", telegram_bot.get_user_role)
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "OK"})
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, _days, context=None: {
            "revenue": 120000.0,
            "payout": 91000.0,
            "cost_price": 45000.0,
            "advertising": 29900.63,
            "logistics": 6300.0,
            "storage": 1200.0,
            "other": 500.0,
            "acquiring": 300.0,
            "deductions": 800.0,
            "unexplained": 1663.27,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": True,
            "official_net_profit": 24336.1,
            "status": "OK",
            "cost_total": 45000.0,
            "logistics_total": 6300.0,
            "storage_total": 1200.0,
            "deductions_total": 800.0,
            "acquiring_total": 300.0,
            "tax_amount": 10000.0,
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": 70000.0,
            "sales_for_pay_total": 91000.0,
            "sales_revenue_total": 120000.0,
            "status": "OK",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None: {
            "coverage_percent": 100.0,
            "logistics": 6300.0,
            "storage": 1200.0,
            "acquiring": 300.0,
            "deductions": 800.0,
            "explicit_other_deductions": 500.0,
            "other_deductions": 500.0,
            "residual_other_deductions": 1663.27,
            "unexplained_total": 1663.27,
            "status": "OK",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_OK",
            "status_kind": "ready",
            "total_spend": 29900.63,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_products_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "cost_coverage_percent": 100.0,
            "known_skus": 14,
            "missing_skus": 0,
            "critical_stock_count": 0,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_data_quality_snapshot",
        lambda _user, _days, context=None: {"overall_status": "HIGH", "sales": {"status": "OK"}},
    )
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "business_health": "OK",
            "business_state": {"sales": "OK", "finance": "OK", "ads": "GOOD"},
            "main_recommendation": "Следить за юнит-экономикой и рекламой.",
            "main_recommendation_action": "Открыть /finance.",
            "today_actions": ["Открыть /advisor."],
            "risks": [],
            "advertising": telegram_bot._advertising_customer_snapshot(user, days),
            "products": telegram_bot._products_center_snapshot(user, days),
            "unified_finance": build_unified_financial_snapshot_dict(user, days, bot=telegram_bot),
        },
    )
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (18, 135000.0, 2, 7000.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (14, 120000.0))
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats",
        lambda _days, _user: (120000.0, 3000.0, 91000.0, 45000.0, 6300.0, 29900.63, 1200.0, 500.0, 85663.9, 0.0, 34336.1, 20.3, 3),
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats_after_tax",
        lambda _days, _user: {
            "profit_before_tax": 34336.1,
            "tax": 10000.0,
            "profit_after_tax": 24336.1,
            "margin_after_tax": 20.3,
            "tax_notes": [],
            "tax_configured": True,
        },
    )


def test_financial_core_snapshot_contract_and_runtime_integrity(monkeypatch):
    _patch_sources(monkeypatch)
    days = ("2026-07-01", "2026-07-31")
    snapshot = build_unified_financial_snapshot_dict(100, days, bot=telegram_bot)

    required_fields = (
        "period_label",
        "buyouts_count",
        "buyout_percent",
        "gross_profit",
        "operating_profit",
        "confirmed_expenses_total",
        "pending_expenses_total",
        "finance_confidence",
        "finance_confidence_score",
        "finance_confidence_reason",
        "profit_display_mode",
        "sales_status",
        "ads_status",
        "data_quality_status",
        "source_map",
        "warnings",
    )
    for field in required_fields:
        assert field in snapshot, field

    for field in ("sales_revenue", "wb_payout", "advertising_spend", "cost_price", "expenses_total", "profit_before_tax", "net_profit"):
        source_payload = dict((snapshot.get("source_map") or {}).get(field) or {})
        assert source_payload.get("selected_source"), field

    handlers = telegram_bot._command_handlers()
    outputs = {}
    for command in ("report", "finance", "pnl", "dashboard", "ceo", "business"):
        update = _Update(f"/{command}")
        context = _Context(["current_month"] if command == "ceo" else [])
        _run(handlers[command](update, context))
        outputs[command] = update.message.replies[-1]

    assert "120 000.00" in outputs["report"]
    assert "29 900.63" in outputs["finance"]
    assert "85 663.90" in outputs["pnl"]
    assert "24 336.10" in outputs["report"]
    assert "24 336.10" in outputs["dashboard"]
    assert "24 336.10" in outputs["ceo"]
    assert "высокая" in outputs["business"].lower()

    audit = build_consistency_audit(100, days, bot=telegram_bot)
    assert not audit["mismatches"]
