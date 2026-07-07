from __future__ import annotations

from datetime import date

from vooglii_finance.customer_snapshot import build_customer_financial_snapshot


def test_customer_snapshot_uses_wb_native_for_closed_period(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 20000.0,
            "wb_payout": 15000.0,
            "logistics": 1000.0,
            "storage": 200.0,
            "acquiring": 100.0,
            "wb_deductions": 500.0,
            "other_expenses": 50.0,
            "advertising_spend": 300.0,
            "profit_before_tax": 4000.0,
            "net_profit": 3500.0,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
        },
    )
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.refresh_wb_financial_period",
        lambda *_args, **_kwargs: {"status": "CLOSED", "source": "finance_raw_audit", "confidence": "high"},
    )
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_wb_weekly_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_count": 31,
            "returns_count": 2,
            "buyouts_count": 31,
            "orders_count": 35,
            "wb_sale_amount": 14046.08,
            "wb_payout_amount": 15327.09,
            "wb_logistics": 3463.06,
            "wb_storage": 631.09,
            "wb_acquiring": 558.14,
            "wb_deductions": 2148.00,
            "wb_total_to_pay": 9084.94,
            "wb_other": 0.0,
            "advertising": 280.0,
        },
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot["source_mode"] == "WB_NATIVE_CLOSED"
    assert snapshot["sales_revenue"] == 14046.08
    assert snapshot["wb_payout"] == 15327.09
    assert snapshot["wb_total_to_pay"] == 9084.94
    assert snapshot["wb_data_status_text"] == "Данные WB: 🟢 период закрыт"


def test_customer_snapshot_uses_operational_for_open_period(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 1200.0,
            "wb_payout": 900.0,
            "logistics": 40.0,
            "storage": 5.0,
            "acquiring": 3.0,
            "wb_deductions": 10.0,
            "other_expenses": 2.0,
            "advertising_spend": 50.0,
            "profit_before_tax": 200.0,
            "net_profit": None,
            "finance_status": "FINANCE_WAITING_WB",
            "finance_confidence": "LOW",
        },
    )
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.refresh_wb_financial_period",
        lambda *_args, **_kwargs: {"status": "OPEN", "source": "current_period", "confidence": "low"},
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 7, 7), date(2026, 7, 8))

    assert snapshot["source_mode"] == "OPERATIONAL_PRELIMINARY"
    assert snapshot["is_preliminary"] is True
    assert snapshot["sales_revenue"] == 1200.0
    assert snapshot["wb_data_status_text"] == "Данные WB: 🟡 данные обновляются"
