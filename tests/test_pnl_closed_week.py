from __future__ import annotations

from datetime import date

import pytest

import telegram_bot

from vooglii_finance.customer_snapshot import build_customer_financial_snapshot


def _patch_closed_week_sources(monkeypatch, case):
    unified_payload = {
        "sales_revenue": case["revenue"],
        "wb_payout": case.get("payout", case["revenue"]),
        "logistics": case["logistics"] + 999.0,
        "storage": case["storage"] + 999.0,
        "acquiring": case["acquiring"] + 999.0,
        "wb_deductions": case["deductions"] + 999.0,
        "other_expenses": case["other"] + 999.0,
        "penalties": case.get("penalties", 0.0),
        "advertising_spend": case["advertising"],
        "cost_price": case["cost"],
        "profit_before_tax": 123456.78,
        "net_profit": None,
        "expenses_total": 987654.32,
        "margin_percent": 0.0,
        "roi_percent": 0.0,
        "finance_status": "FINANCE_WAITING_WB",
        "finance_confidence": "LOW",
        "finance_confidence_score": 30,
        "finance_confidence_reason": "before_closed_override",
        "profit_display_mode": "HIDDEN",
        "source_map": {
            "sales_revenue": {"selected_source": "legacy.revenue"},
            "wb_payout": {"selected_source": "legacy.payout"},
            "advertising_spend": {"selected_source": "finance_expense_events.advertising"},
            "cost_price": {"selected_source": "product_catalog.cost_price"},
            "profit_before_tax": {"selected_source": "legacy.derived"},
            "expenses_total": {"selected_source": "legacy.expenses_total"},
        },
    }
    wb_payload = {
        "sales_count": 10,
        "returns_count": 1,
        "buyouts_count": 10,
        "orders_count": 12,
        "wb_sale_amount": case["revenue"],
        "wb_payout_amount": case.get("payout", case["revenue"] * 0.9),
        "wb_total_to_pay": case.get("total_to_pay", 1.0),
        "wb_logistics": case["logistics"],
        "wb_storage": case["storage"],
        "wb_acquiring": case["acquiring"],
        "wb_deductions": case["deductions"],
        "wb_other": case["other"],
        "penalties": case.get("penalties", 0.0),
        "advertising": case["advertising"],
        "source_map": {
            "wb_sale_amount": {"selected_source": "payment_reports.revenue", "selected_value": case["revenue"], "source_table": "payment_reports_rows", "source_column": "revenue"},
            "wb_payout_amount": {"selected_source": "payment_reports.for_pay", "selected_value": case.get("payout", case["revenue"] * 0.9), "source_table": "payment_reports_rows", "source_column": "for_pay"},
            "wb_total_to_pay": {"selected_source": "payment_reports.bank_payment", "selected_value": case.get("total_to_pay", 1.0), "source_table": "payment_reports_rows", "source_column": "bank_payment"},
            "wb_logistics": {"selected_source": "payment_reports.delivery", "selected_value": case["logistics"], "source_table": "payment_reports_rows", "source_column": "delivery"},
            "wb_storage": {"selected_source": "payment_reports.storage", "selected_value": case["storage"], "source_table": "payment_reports_rows", "source_column": "storage"},
            "wb_acquiring": {"selected_source": "finance_raw_audit.acquiring_fee", "selected_value": case["acquiring"], "source_table": "finance_raw_audit", "source_column": "acquiring_fee"},
            "wb_deductions": {"selected_source": "payment_reports.deduction", "selected_value": case["deductions"], "source_table": "payment_reports_rows", "source_column": "deduction"},
            "wb_other": {"selected_source": "finance_expense_events.other", "selected_value": case["other"], "source_table": "finance_expense_events", "source_column": "amount"},
            "penalties": {"selected_source": "finance_expense_events.penalties", "selected_value": case.get("penalties", 0.0), "source_table": "finance_expense_events", "source_column": "amount"},
            "advertising": {"selected_source": "finance_expense_events.advertising", "selected_value": case["advertising"], "source_table": "finance_expense_events", "source_column": "amount"},
        },
    }
    monkeypatch.setattr("vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict", lambda *_args, **_kwargs: unified_payload)
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.refresh_wb_financial_period",
        lambda *_args, **_kwargs: {"status": "CLOSED", "source": "finance_raw_audit", "confidence": "high"},
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.build_wb_weekly_snapshot_dict", lambda *_args, **_kwargs: wb_payload)
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda *_args, **_kwargs: None)


@pytest.mark.parametrize(
    "case",
    [
        {
            "period": ("2026-06-08", "2026-06-14"),
            "revenue": 52383.71,
            "cost": 22529.00,
            "advertising": 11667.07,
            "logistics": 15356.67,
            "storage": 706.98,
            "acquiring": 2442.61,
            "deductions": 12699.00,
            "other": 0.0,
            "penalties": 0.0,
            "expected_profit": -13017.62,
        },
        {
            "period": ("2026-06-15", "2026-06-21"),
            "revenue": 29610.83,
            "cost": 10471.00,
            "advertising": 7309.99,
            "logistics": 7443.88,
            "storage": 668.81,
            "acquiring": 1196.97,
            "deductions": 7097.00,
            "other": 0.0,
            "penalties": 0.0,
            "expected_profit": -4576.82,
        },
        {
            "period": ("2026-06-22", "2026-06-28"),
            "revenue": 8395.94,
            "cost": 4083.00,
            "advertising": 4115.95,
            "logistics": 3715.87,
            "storage": 648.74,
            "acquiring": 485.16,
            "deductions": 4040.00,
            "other": 10.0,
            "penalties": 0.0,
            "expected_profit": -8702.78,
        },
        {
            "period": ("2026-06-29", "2026-07-05"),
            "revenue": 14046.08,
            "cost": 5407.00,
            "advertising": 2177.24,
            "logistics": 3463.06,
            "storage": 631.09,
            "acquiring": 558.14,
            "deductions": 2148.00,
            "other": 0.0,
            "penalties": 0.0,
            "expected_profit": -338.45,
        },
    ],
)
def test_closed_week_operational_profit_uses_single_customer_snapshot_formula(monkeypatch, case):
    _patch_closed_week_sources(monkeypatch, case)

    period_from = date.fromisoformat(case["period"][0])
    period_to = date.fromisoformat(case["period"][1])
    snapshot = build_customer_financial_snapshot(42, period_from, period_to)

    assert snapshot.source_mode == "WB_NATIVE_CLOSED"
    assert snapshot.operational_profit == case["expected_profit"]
    assert snapshot.profit_before_tax == case["expected_profit"]
    assert snapshot.expenses_total == round(case["revenue"] - case["expected_profit"], 2)
    assert snapshot.finance_status == "FINANCE_OK"
    assert snapshot.finance_confidence == "HIGH"
    assert snapshot.field_trace["operational_profit"]["selected_reason"] == "closed_customer_snapshot_formula"
    assert snapshot.field_trace["operational_profit"]["selected_source"] == "derived_sales_revenue_minus_expenses_total"
    assert snapshot.field_trace["operational_profit"]["sum"] == snapshot.operational_profit
    assert snapshot.field_trace["expenses_total"]["selected_source"] == "derived_sum"
    assert snapshot.field_trace["expenses_total"]["sum"] == snapshot.expenses_total
    assert snapshot.net_profit is None
    assert snapshot.wb_total_to_pay != snapshot.expenses_total
    assert snapshot.wb_payout_amount != snapshot.expenses_total


def test_closed_week_report_finance_and_pnl_use_same_operational_profit(monkeypatch):
    case = {
        "period": ("2026-06-29", "2026-07-05"),
        "revenue": 14046.08,
        "cost": 5407.00,
        "advertising": 2177.24,
        "logistics": 3463.06,
        "storage": 631.09,
        "acquiring": 558.14,
        "deductions": 2148.00,
        "other": 0.0,
        "penalties": 0.0,
        "expected_profit": -338.45,
    }
    _patch_closed_week_sources(monkeypatch, case)

    snapshot = build_customer_financial_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")

    report_text = telegram_bot._unified_report_text(42, case["period"])
    pnl_text = telegram_bot._pnl_customer_text(42, case["period"])
    finance_text = telegram_bot._finance_center_text(42, case["period"])

    assert "-338.45" in report_text
    assert "-338.45" in pnl_text
    assert "-338.45" in finance_text
    assert "Чистая прибыль: не рассчитана" in report_text
    assert "Р Р°СЃС…РѕРґС‹ (С‡Р°СЃС‚РёС‡РЅРѕ)" not in pnl_text
