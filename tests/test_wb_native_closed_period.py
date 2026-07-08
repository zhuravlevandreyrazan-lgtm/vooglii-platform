from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_finance.customer_snapshot import FrozenSnapshot


def _closed_snapshot(*, total_to_pay: float | None = 9084.94) -> FrozenSnapshot:
    return FrozenSnapshot(
        {
            "orders_count": 35,
            "buyouts_count": 31,
            "returns_count": 2,
            "sales_revenue": 14046.08,
            "wb_sale_amount": 14046.08,
            "wb_payout": 15327.09,
            "wb_payout_amount": 15327.09,
            "logistics": 3463.06,
            "wb_logistics": 3463.06,
            "storage": 631.09,
            "wb_storage": 631.09,
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
            "field_trace": {},
        }
    )


def test_report_uses_wb_native_totals_for_closed_week(monkeypatch):
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: _closed_snapshot())
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")

    text = telegram_bot._unified_report_text(42, ("2026-06-29", "2026-07-05"))

    assert "Данные WB: 🟢 период закрыт" in text
    assert "Продажа WB: 14 046.08" in text
    assert "К выплате WB: 15 327.09" in text
    assert "Итого к оплате WB: 9 084.94" in text
    assert "Дополнительно для управления:" in text


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

    assert "Итого к оплате WB: ожидает данные" in text
