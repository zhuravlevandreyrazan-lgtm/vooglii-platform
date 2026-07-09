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

from vooglii_finance.customer_snapshot import FrozenSnapshot


class _Message:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _Update:
    def __init__(self):
        self.message = _Message()
        self.effective_user = SimpleNamespace(id=42, username="owner")


def _closed_snapshot(
    *,
    logistics: float | None = 3463.06,
    storage: float | None = 631.09,
    total_to_pay: float | None = 9084.94,
    logistics_source: str = "payment_reports.delivery",
    storage_source: str = "payment_reports.storage",
    total_to_pay_source: str = "payment_reports.bank_payment",
) -> FrozenSnapshot:
    return FrozenSnapshot(
        {
            "orders_count": 35,
            "buyouts_count": 31,
            "returns_count": 2,
            "sales_revenue": 14046.08,
            "wb_sale_amount": 14046.08,
            "wb_payout": 15327.09,
            "wb_payout_amount": 15327.09,
            "logistics": logistics,
            "wb_logistics": logistics,
            "storage": storage,
            "wb_storage": storage,
            "acquiring": 558.14,
            "wb_acquiring": 558.14,
            "wb_deductions": 2148.00,
            "wb_total_to_pay": total_to_pay,
            "wb_other": 0.0,
            "other_expenses": 0.0,
            "advertising_spend": 500.0,
            "advertising": 500.0,
            "cost_price": 4000.0,
            "profit_before_tax": 1200.0,
            "operational_profit": 1200.0,
            "net_profit": 1000.0,
            "expenses_total": 7300.0,
            "margin_percent": 7.1,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
            "source_mode": "WB_NATIVE_CLOSED",
            "is_preliminary": False,
            "cost_status": "FULL",
            "wb_data_status_text": "Данные WB: 🟢 период закрыт",
            "field_trace": {
                "wb_logistics": {
                    "value": logistics,
                    "selected_source": logistics_source,
                    "selected_table": "payment_reports_rows",
                    "selected_column": "delivery",
                    "selected_reason": "closed_wb_period_uses_wb_weekly_snapshot",
                },
                "wb_storage": {
                    "value": storage,
                    "selected_source": storage_source,
                    "selected_table": "payment_reports_rows",
                    "selected_column": "storage",
                    "selected_reason": "closed_wb_period_uses_wb_weekly_snapshot",
                },
                "wb_total_to_pay": {
                    "value": total_to_pay,
                    "selected_source": total_to_pay_source,
                    "selected_table": "payment_reports_rows",
                    "selected_column": "bank_payment",
                    "selected_reason": "closed_wb_period_uses_wb_weekly_snapshot",
                },
            },
        }
    )


def test_report_uses_wb_native_totals_for_closed_week(monkeypatch):
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: _closed_snapshot())
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")

    text = telegram_bot._unified_report_text(42, ("2026-06-29", "2026-07-05"))

    for expected_text in ("14 046.08 ₽", "15 327.09 ₽", "3 463.06 ₽", "631.09 ₽", "2 148.00 ₽", "9 084.94 ₽"):
        assert expected_text in text


def test_finance_and_pnl_closed_week_do_not_duplicate_or_downgrade_wb_status(monkeypatch):
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: _closed_snapshot())
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "_financial_engine_snapshot", lambda *_args, **_kwargs: {"status": "OK", "official_new_finance_available": True, "official_net_profit": 1000.0})
    monkeypatch.setattr(telegram_bot, "_payment_reconciliation_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "get_finance_difference_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "_advertising_customer_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "_report_mgmt_snapshot", lambda *_args, **_kwargs: {"status": "OK"})

    finance_text = telegram_bot._finance_center_text(42, ("2026-06-29", "2026-07-05"))
    pnl_text = telegram_bot._pnl_customer_text(42, ("2026-06-29", "2026-07-05"))

    assert finance_text.count("Данные WB: 🟢 период закрыт") == 1
    assert "Расходы (частично)" not in pnl_text


def test_closed_week_report_shows_waiting_text_when_total_to_pay_missing(monkeypatch):
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: _closed_snapshot(total_to_pay=None))
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")

    text = telegram_bot._unified_report_text(42, ("2026-06-29", "2026-07-05"))

    assert "ожидает данные" in text
    assert "9 084.94 ₽" not in text


def test_finance_explain_closed_week_shows_wb_weekly_selected_sources(monkeypatch):
    async def _access(*_args, **_kwargs):
        return True

    async def _send_long(update, text, **_kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: _closed_snapshot())

    update = _Update()
    asyncio.run(legacy_bot.finance_explain_command(update, SimpleNamespace(args=[]), "29.06.2026 - 05.07.2026", ("2026-06-29", "2026-07-05"), 42))
    text = update.message.replies[-1]

    assert "payment_reports.delivery" in text
    assert "payment_reports.storage" in text
    assert "payment_reports.bank_payment" in text
    assert "finance_raw_audit" not in text


def test_finance_explain_closed_week_shows_missing_official_sources(monkeypatch):
    async def _access(*_args, **_kwargs):
        return True

    async def _send_long(update, text, **_kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(
        legacy_bot,
        "_customer_financial_snapshot",
        lambda *_args, **_kwargs: _closed_snapshot(
            logistics=None,
            storage=None,
            total_to_pay=None,
            logistics_source="payment_reports.missing",
            storage_source="payment_reports.missing",
            total_to_pay_source="payment_reports.missing",
        ),
    )

    update = _Update()
    asyncio.run(legacy_bot.finance_explain_command(update, SimpleNamespace(args=[]), "29.06.2026 - 05.07.2026", ("2026-06-29", "2026-07-05"), 42))
    text = update.message.replies[-1]

    assert text.count("payment_reports.missing") >= 3


def test_report_shows_retail_amount_sum_week_revenue(monkeypatch):
    retail_week_snapshot = FrozenSnapshot(
        {
            **dict(_closed_snapshot()),
            "sales_revenue": 8395.94,
            "wb_sale_amount": 8395.94,
            "wb_payout": 8100.00,
            "wb_payout_amount": 8100.00,
            "wb_total_to_pay": 4600.00,
        }
    )
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: retail_week_snapshot)
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "22.06.2026 - 28.06.2026")

    text = telegram_bot._unified_report_text(42, ("2026-06-22", "2026-06-28"))

    assert "8 395.94" in text
