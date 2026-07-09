from __future__ import annotations

from datetime import date

from vooglii_finance.customer_snapshot import build_customer_financial_snapshot


def test_customer_snapshot_uses_wb_native_selected_sources_for_closed_period(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 20000.0,
            "wb_payout": 15000.0,
            "logistics": 3613.80,
            "storage": 540.29,
            "acquiring": 100.0,
            "wb_deductions": 500.0,
            "other_expenses": 50.0,
            "advertising_spend": 300.0,
            "profit_before_tax": 4000.0,
            "net_profit": 3500.0,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
            "source_map": {
                "cost_price": {"selected_source": "catalog.cost"},
                "profit_before_tax": {"selected_source": "derived"},
                "net_profit": {"selected_source": "engine.net_profit"},
            },
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
            "wb_sale_amount": 999999.99,
            "wb_payout_amount": 999999.99,
            "wb_logistics": 999999.99,
            "wb_storage": 999999.99,
            "wb_acquiring": 999999.99,
            "wb_deductions": 999999.99,
            "wb_total_to_pay": 999999.99,
            "wb_other": 0.0,
            "advertising": 280.0,
            "source_map": {
                "wb_sale_amount": {"selected_source": "payment_reports.revenue", "selected_value": 14046.08, "source_table": "payment_reports_rows", "source_column": "revenue"},
                "wb_payout_amount": {"selected_source": "payment_reports.for_pay", "selected_value": 15327.09, "source_table": "payment_reports_rows", "source_column": "for_pay"},
                "wb_logistics": {"selected_source": "payment_reports.delivery", "selected_value": 3463.06, "source_table": "payment_reports_rows", "source_column": "delivery"},
                "wb_storage": {"selected_source": "payment_reports.storage", "selected_value": 631.09, "source_table": "payment_reports_rows", "source_column": "storage"},
                "wb_acquiring": {"selected_source": "finance_raw_audit.acquiring_fee", "selected_value": 558.14, "source_table": "finance_raw_audit", "source_column": "acquiring_fee"},
                "wb_deductions": {"selected_source": "payment_reports.deduction", "selected_value": 2148.00, "source_table": "payment_reports_rows", "source_column": "deduction"},
                "wb_total_to_pay": {"selected_source": "payment_reports.bank_payment", "selected_value": 9084.94, "source_table": "payment_reports_rows", "source_column": "bank_payment"},
                "advertising": {"selected_source": "finance_expense_events.advertising", "selected_value": 280.0, "source_table": "finance_expense_events", "source_column": "amount"},
            },
        },
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot.source_mode == "WB_NATIVE_CLOSED"
    assert snapshot.sales_revenue == 14046.08
    assert snapshot.wb_sale_amount == 14046.08
    assert snapshot.wb_payout_amount == 15327.09
    assert snapshot.wb_total_to_pay == 9084.94
    assert snapshot.wb_logistics == 3463.06
    assert snapshot.wb_storage == 631.09
    assert snapshot.field_trace["wb_logistics"]["selected_source"] == "payment_reports.delivery"
    assert snapshot.field_trace["wb_storage"]["selected_source"] == "payment_reports.storage"
    assert snapshot.field_trace["wb_total_to_pay"]["selected_source"] == "payment_reports.bank_payment"
    assert snapshot.field_trace["wb_storage"]["selected_column"] == "storage"
    assert snapshot.wb_data_status_text == "Данные WB: 🟢 период закрыт"
    assert snapshot.net_profit is None
    assert snapshot.official_net_profit is None
    assert snapshot.field_trace["expenses_total"]["selected_source"] == "derived_sum"
    assert snapshot.field_trace["operational_profit"]["selected_source"] == "derived_sales_revenue_minus_expenses_total"
    assert snapshot.field_trace["expenses_total"]["sum"] == snapshot.expenses_total
    assert snapshot.field_trace["operational_profit"]["sum"] == snapshot.operational_profit
    assert "Налоговый режим не настроен. Чистая прибыль после налога не рассчитана." in snapshot.warnings


def test_customer_snapshot_closed_period_keeps_none_total_to_pay_without_payout_fallback(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 20000.0,
            "wb_payout": 15327.09,
            "logistics": 3613.80,
            "storage": 540.29,
            "acquiring": 558.14,
            "wb_deductions": 2148.00,
            "other_expenses": 50.0,
            "advertising_spend": 300.0,
            "profit_before_tax": 4000.0,
            "net_profit": 3500.0,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
            "source_map": {},
        },
    )
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.refresh_wb_financial_period",
        lambda *_args, **_kwargs: {"status": "CLOSED", "source": "finance_raw_audit", "confidence": "high"},
    )
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_wb_weekly_snapshot_dict",
        lambda *_args, **_kwargs: {
            "wb_total_to_pay": 123.45,
            "wb_logistics": 3613.80,
            "wb_storage": 540.29,
            "source_map": {
                "wb_total_to_pay": {
                    "selected_source": "payment_reports.missing",
                    "selected_value": None,
                    "source_table": "payment_reports_rows",
                    "source_column": "bank_payment",
                },
                "wb_logistics": {
                    "selected_source": "payment_reports.missing",
                    "selected_value": None,
                    "source_table": "payment_reports_rows",
                    "source_column": "delivery",
                },
                "wb_storage": {
                    "selected_source": "payment_reports.missing",
                    "selected_value": None,
                    "source_table": "payment_reports_rows",
                    "source_column": "storage",
                },
            },
        },
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot.source_mode == "WB_NATIVE_CLOSED"
    assert snapshot.wb_total_to_pay is None
    assert snapshot.wb_logistics is None
    assert snapshot.wb_storage is None
    assert snapshot.field_trace["wb_total_to_pay"]["selected_source"] == "payment_reports.missing"
    assert snapshot.field_trace["wb_logistics"]["selected_source"] == "payment_reports.missing"
    assert snapshot.field_trace["wb_storage"]["selected_source"] == "payment_reports.missing"


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
            "source_map": {
                "sales_revenue": {"selected_source": "sales"},
                "wb_payout": {"selected_source": "sales.for_pay"},
                "logistics": {"selected_source": "expenses.logistics"},
                "storage": {"selected_source": "expenses.storage"},
                "acquiring": {"selected_source": "finance_raw_audit.acquiring_fee"},
                "wb_deductions": {"selected_source": "finance_raw_audit.deduction"},
                "advertising_spend": {"selected_source": "advertising.total_spend"},
                "cost_price": {"selected_source": "catalog.cost"},
                "profit_before_tax": {"selected_source": "derived"},
                "net_profit": {"selected_source": None},
            },
        },
    )
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.refresh_wb_financial_period",
        lambda *_args, **_kwargs: {"status": "OPEN", "source": "current_period", "confidence": "low"},
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 7, 7), date(2026, 7, 8))

    assert snapshot.source_mode == "OPERATIONAL_PRELIMINARY"
    assert snapshot.is_preliminary is True
    assert snapshot.sales_revenue == 1200.0
    assert snapshot.operational_profit == 200.0
    assert snapshot.field_trace["wb_sale_amount"]["selected_source"] == "sales"
    assert snapshot.wb_data_status_text == "Данные WB: 🟡 данные обновляются"
