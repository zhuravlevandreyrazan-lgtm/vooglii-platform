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


def _patch_unified_sources(monkeypatch, *, finance_ready: bool = True):
    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: (1, "owner_user", "token", "PRO", None, None, None, "owner", None))
    monkeypatch.setattr(legacy_bot, "get_user", telegram_bot.get_user)
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "OK" if finance_ready else "WAITING"})
    monkeypatch.setattr(legacy_bot, "_finance_api_status_snapshot", telegram_bot._finance_api_status_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, _days, context=None: {
            "revenue": 120000.0,
            "payout": 91000.0,
            "cost_price": 45000.0,
            "advertising": 29900.63,
            "logistics": 6300.0 if finance_ready else 0.0,
            "storage": 1200.0 if finance_ready else 0.0,
            "other": 500.0 if finance_ready else 0.0,
            "acquiring": 300.0 if finance_ready else 0.0,
            "deductions": 800.0 if finance_ready else 0.0,
            "external_expenses": 500.0 if finance_ready else 0.0,
            "unexplained": 1663.27 if finance_ready else 0.0,
            "management_profit": 16100.0,
            "management_profit_with_storage": 14900.0,
            "management_margin": 13.4,
            "management_roi": 20.1,
            "period_start": "2026-07-01",
            "period_end": "2026-07-31",
        },
    )
    monkeypatch.setattr(legacy_bot, "_report_mgmt_snapshot", telegram_bot._report_mgmt_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": finance_ready,
            "official_net_profit": 24336.1 if finance_ready else None,
            "status": "OK" if finance_ready else "OFFICIAL_NEW_FINANCE_UNAVAILABLE",
        },
    )
    monkeypatch.setattr(legacy_bot, "_financial_engine_snapshot", telegram_bot._financial_engine_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": 70000.0,
            "sales_for_pay_total": 91000.0,
            "status": "OK",
        },
    )
    monkeypatch.setattr(legacy_bot, "_payment_reconciliation_snapshot", telegram_bot._payment_reconciliation_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None: {
            "coverage_percent": 100.0 if finance_ready else 0.0,
            "logistics": 6300.0 if finance_ready else 0.0,
            "storage": 1200.0 if finance_ready else 0.0,
            "residual_other_deductions": 1663.27 if finance_ready else 0.0,
            "status": "OK" if finance_ready else "WAITING_WB",
        },
    )
    monkeypatch.setattr(legacy_bot, "get_finance_difference_snapshot", telegram_bot.get_finance_difference_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_PARTIAL",
            "status_kind": "error",
            "raw_status": "ADS_PARTIAL",
            "last_success": "2026-07-01 10:00:00",
            "total_spend": 29900.63,
            "linked_spend": 26000.00,
            "unlinked_spend": 3900.63,
            "linkability_percent": 86.9,
            "campaigns_total": 10,
            "campaigns_linked": 8,
            "campaigns_unlinked": 2,
            "status": "MEDIUM",
            "drr": 24.9,
            "roas": 4.01,
            "cpc": 15.2,
            "ctr": 1.9,
            "cpa": 210.4,
            "coverage_percent": 100.0,
            "delta": 1663.27,
        },
    )
    monkeypatch.setattr(legacy_bot, "_advertising_customer_snapshot", telegram_bot._advertising_customer_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_products_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "cost_coverage_percent": 100.0,
            "known_skus": 14,
            "missing_skus": 0,
            "critical_stock_count": 0,
            "stock_snapshot_date": "2026-07-05",
        },
    )
    monkeypatch.setattr(legacy_bot, "_products_center_snapshot", telegram_bot._products_center_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "business_health": "WARNING",
            "business_state": {"sales": "GOOD", "finance": "BLOCKED", "ads": "GOOD"},
            "main_recommendation": "Проверить финансовые данные WB.",
            "main_recommendation_action": "Открыть /finance.",
            "risks": ["Финансовые данные WB ещё не подтверждены"],
            "today_actions": ["Открыть /advisor"],
            "advertising": telegram_bot._advertising_customer_snapshot(user, days),
            "products": telegram_bot._products_center_snapshot(user, days),
            "unified_finance": build_unified_financial_snapshot_dict(user, days, bot=telegram_bot),
        },
    )
    monkeypatch.setattr(legacy_bot, "_business_center_snapshot", telegram_bot._business_center_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_system_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "agent_status": "OK",
            "database_status": "OK",
            "sales_status": "OK",
            "finance_status": "FINANCE_OK" if finance_ready else "FINANCE_WAITING_WB",
            "ads_status": "OK",
            "advertising": telegram_bot._advertising_customer_snapshot(user, days),
            "wb_connected": True,
            "last_updates": {"sales": "2026-07-05 11:30:00"},
            "product_readiness": "READY",
            "structure_status": "READY",
            "known_blockers": [],
            "engineering_commands": [],
            "unified_finance": build_unified_financial_snapshot_dict(user, days, bot=telegram_bot),
        },
    )
    monkeypatch.setattr(legacy_bot, "_system_center_snapshot", telegram_bot._system_center_snapshot)
    monkeypatch.setattr(telegram_bot, "_data_quality_snapshot", lambda _user, _days, context=None: {"overall_status": "HIGH"})
    monkeypatch.setattr(legacy_bot, "_data_quality_snapshot", telegram_bot._data_quality_snapshot)
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (18, 135000.0, 2, 7000.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (14, 120000.0))
    monkeypatch.setattr(legacy_bot, "get_orders_stats", telegram_bot.get_orders_stats)
    monkeypatch.setattr(legacy_bot, "get_period_stats", telegram_bot.get_period_stats)
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats",
        lambda _days, _user: (120000.0, 3000.0, 91000.0, 45000.0, 6300.0, 29900.63, 1200.0, 500.0, 85663.9, 0.0, 34336.1, 20.3, 3),
    )
    monkeypatch.setattr(legacy_bot, "get_profit_stats", telegram_bot.get_profit_stats)
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats_after_tax",
        lambda _days, _user: {
            "profit_before_tax": 34336.1,
            "tax": 10000.0 if finance_ready else 0.0,
            "profit_after_tax": 24336.1 if finance_ready else 0.0,
            "margin_after_tax": 20.3,
            "tax_notes": [],
            "tax_configured": finance_ready,
        },
    )
    monkeypatch.setattr(legacy_bot, "get_profit_stats_after_tax", telegram_bot.get_profit_stats_after_tax)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda _user_id: "owner")
    monkeypatch.setattr(legacy_bot, "get_user_role", telegram_bot.get_user_role)


def test_unified_snapshot_keeps_customer_financial_screens_consistent(monkeypatch):
    _patch_unified_sources(monkeypatch, finance_ready=True)
    handlers = telegram_bot._command_handlers()

    unified = build_unified_financial_snapshot_dict(100, ("2026-07-01", "2026-07-31"), bot=telegram_bot)
    assert abs(float(unified["advertising_spend"] or 0) - 29900.63) <= 0.01
    assert abs(float(unified["cost_price"] or 0) - 45000.0) <= 0.01
    assert abs(float(unified["expenses_total"] or 0) - 85663.9) <= 0.01
    assert abs(float(unified["net_profit"] or 0) - 24336.1) <= 0.01
    assert unified["finance_status"] == "FINANCE_OK"

    outputs = {}
    for command in ("business", "finance", "pnl", "report", "dashboard", "ceo", "system"):
        update = _Update(f"/{command}")
        context = _Context(["current_month"] if command in ("pnl", "ceo") else [])
        _run(handlers[command](update, context))
        outputs[command] = update.message.replies[-1]

    assert "29 900.63" in outputs["business"]
    assert "Реклама WB: 29 900.63" in outputs["finance"]
    assert "Себестоимость: 45 000.00" in outputs["finance"]
    assert "Расходы: 85 663.90" in outputs["pnl"]
    assert "Чистая прибыль: 24 336.10" in outputs["report"]
    assert "Чистая прибыль: 24 336.10" in outputs["dashboard"]
    assert "Чистая прибыль: 24 336.10" in outputs["ceo"]
    assert "Финансовые данные WB: доступны" in outputs["system"]

    audit = build_consistency_audit(100, ("2026-07-01", "2026-07-31"), bot=telegram_bot)
    assert not audit["mismatches"]


def test_unified_snapshot_avoids_false_zero_when_finance_is_waiting(monkeypatch):
    _patch_unified_sources(monkeypatch, finance_ready=False)

    finance_text = telegram_bot._finance_center_text(100, ("2026-07-01", "2026-07-31"))
    pnl_text = telegram_bot._pnl_customer_text(100, ("2026-07-01", "2026-07-31"))

    assert "Логистика WB: 0.00 ₽" not in finance_text
    assert "Хранение WB: 0.00 ₽" not in finance_text
    assert "Эквайринг WB: 0.00 ₽" not in finance_text
    assert "Прибыль: 0.00 ₽" not in pnl_text
    assert "ожидают подтверждения" in finance_text
    assert "пока не рассчитана" in pnl_text
