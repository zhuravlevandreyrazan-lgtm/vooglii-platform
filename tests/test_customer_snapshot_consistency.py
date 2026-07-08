from __future__ import annotations

from datetime import date

from vooglii_finance.customer_snapshot import FrozenSnapshot
from vooglii_finance.customer_snapshot import build_customer_financial_snapshot
import telegram_bot


def _snapshot() -> FrozenSnapshot:
    payload = {
        "source_mode": "WB_NATIVE_CLOSED",
        "is_preliminary": False,
        "finance_status": "FINANCE_OK",
        "finance_confidence": "HIGH",
        "finance_confidence_score": 100.0,
        "advertising_status": "ADS_OK",
        "cost_status": "COST_OK",
        "wb_data_status_text": "Данные WB: 🟢 период закрыт",
        "wb_sale_amount": 14046.08,
        "sales_revenue": 14046.08,
        "wb_payout_amount": 15327.09,
        "wb_payout": 15327.09,
        "wb_total_to_pay": 9084.94,
        "wb_logistics": 3463.06,
        "logistics": 3463.06,
        "wb_storage": 631.09,
        "storage": 631.09,
        "wb_acquiring": 558.14,
        "acquiring": 558.14,
        "wb_deductions": 2148.00,
        "advertising": 500.0,
        "advertising_spend": 500.0,
        "cost_price": 4000.0,
        "operational_profit": 1200.0,
        "profit_before_tax": 1200.0,
        "net_profit": 1000.0,
        "expenses_total": 7300.0,
        "other_expenses": 0.0,
        "wb_other": 0.0,
        "orders_count": 35,
        "buyouts_count": 31,
        "returns_count": 2,
        "margin_percent": 7.1,
        "warnings": [],
        "field_trace": {
            key: {
                "value": value,
                "selected_source": "snapshot",
                "selected_table": "customer_snapshot",
                "selected_column": key,
                "selected_reason": "consistency_test",
            }
            for key, value in {
                "wb_sale_amount": 14046.08,
                "wb_payout_amount": 15327.09,
                "wb_total_to_pay": 9084.94,
                "wb_logistics": 3463.06,
                "wb_storage": 631.09,
                "wb_deductions": 2148.00,
                "wb_acquiring": 558.14,
                "advertising": 500.0,
                "cost_price": 4000.0,
                "operational_profit": 1200.0,
            }.items()
        },
    }
    return FrozenSnapshot(payload)


def test_customer_snapshot_consistency_across_customer_surfaces(monkeypatch):
    snapshot = _snapshot()
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(telegram_bot, "_snapshot_context", lambda: {})
    monkeypatch.setattr(telegram_bot, "_director_lightweight_context", lambda *_args, **_kwargs: {"financial_engine_snapshot": {}, "ads_snapshot": {}, "sku_registry_snapshot": {}})
    monkeypatch.setattr(telegram_bot, "_health_snapshot", lambda *_args, **_kwargs: {"quality": {"sales": {"status": "OK"}, "advertising": {"status": "OK"}}, "last_updates": {}, "database_status": "OK"})
    monkeypatch.setattr(telegram_bot, "get_user", lambda *_args, **_kwargs: (None, None, "token"))
    monkeypatch.setattr(telegram_bot, "_director_snapshot", lambda *_args, **_kwargs: {"business_health": "OK", "business_state": {"sales": "OK", "ads": "OK"}, "executive_summary": "ok", "main_action": {"message": "act"}, "main_risk": {"title": "risk"}, "today_focus": ["focus"]})
    monkeypatch.setattr(telegram_bot, "_advisor_v2_snapshot", lambda *_args, **_kwargs: {"main_recommendation": {"title": "title", "action": "action"}, "risks": []})
    monkeypatch.setattr(telegram_bot, "_cfo_insights_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "_kpi_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "_decision_snapshot", lambda *_args, **_kwargs: {"status": "OK", "top_actions": []})
    monkeypatch.setattr(telegram_bot, "_advertising_customer_snapshot", lambda *_args, **_kwargs: {"status": "OK", "total_spend": 500.0})
    monkeypatch.setattr(telegram_bot, "_products_center_snapshot", lambda *_args, **_kwargs: {"critical_stock_count": 0, "missing_skus": 0, "cost_coverage_percent": 100.0})

    home = telegram_bot._home_snapshot(42, ("2026-06-29", "2026-07-05"))
    business = telegram_bot._business_center_snapshot(42, ("2026-06-29", "2026-07-05"))
    finance = telegram_bot._finance_center_snapshot(42, ("2026-06-29", "2026-07-05"))
    report = telegram_bot._customer_report_snapshot(42, ("2026-06-29", "2026-07-05"))
    pnl = telegram_bot._customer_pnl_snapshot(42, ("2026-06-29", "2026-07-05"))
    dashboard = telegram_bot._customer_dashboard_snapshot(42, ("2026-06-29", "2026-07-05"))

    for field_name, expected_value in telegram_bot._customer_financial_values(snapshot).items():
        assert home[field_name] == expected_value
        assert business[field_name] == expected_value
        assert finance[field_name] == expected_value
        assert report[field_name] == expected_value
        assert pnl[field_name] == expected_value
        assert dashboard[field_name] == expected_value


def test_customer_snapshot_closed_period_matches_wb_weekly_selected_values(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 37624.19,
            "wb_payout": 15327.09,
            "logistics": 3613.80,
            "storage": 540.29,
            "acquiring": 558.14,
            "wb_deductions": 2148.00,
            "other_expenses": 0.0,
            "advertising_spend": 500.0,
            "profit_before_tax": 1200.0,
            "net_profit": 1000.0,
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
            "wb_sale_amount": 14046.08,
            "wb_payout_amount": 15327.09,
            "wb_total_to_pay": 0.0,
            "wb_logistics": 0.0,
            "wb_storage": 0.0,
            "wb_acquiring": 0.0,
            "wb_deductions": 0.0,
            "wb_other": 0.0,
            "source_map": {
                "wb_sale_amount": {"selected_source": "payment_reports.revenue", "selected_value": 14046.08},
                "wb_payout_amount": {"selected_source": "payment_reports.for_pay", "selected_value": 15327.09},
                "wb_total_to_pay": {"selected_source": "payment_reports.bank_payment", "selected_value": 9084.94},
                "wb_logistics": {"selected_source": "payment_reports.delivery", "selected_value": 3463.06},
                "wb_storage": {"selected_source": "payment_reports.storage", "selected_value": 631.09},
                "wb_acquiring": {"selected_source": "finance_raw_audit.acquiring_fee", "selected_value": 558.14},
                "wb_deductions": {"selected_source": "payment_reports.deduction", "selected_value": 2148.00},
                "wb_other": {"selected_source": "finance_expense_events.other", "selected_value": 0.0},
            },
        },
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot.wb_logistics == 3463.06
    assert snapshot.wb_storage == 631.09
    assert snapshot.wb_total_to_pay == 9084.94
    assert snapshot.wb_total_to_pay != snapshot.wb_payout_amount
    assert snapshot.field_trace["wb_logistics"]["selected_source"] == "payment_reports.delivery"
    assert snapshot.field_trace["wb_storage"]["selected_source"] == "payment_reports.storage"
    assert snapshot.field_trace["wb_total_to_pay"]["selected_source"] == "payment_reports.bank_payment"


def test_customer_snapshot_closed_period_marks_missing_official_weekly_fields(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.customer_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 14046.08,
            "wb_payout": 15327.09,
            "logistics": 3613.80,
            "storage": 540.29,
            "acquiring": 558.14,
            "wb_deductions": 2148.00,
            "other_expenses": 0.0,
            "advertising_spend": 500.0,
            "profit_before_tax": 1200.0,
            "net_profit": 1000.0,
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
            "wb_sale_amount": 14046.08,
            "wb_payout_amount": 15327.09,
            "wb_total_to_pay": 15327.09,
            "wb_logistics": 3613.80,
            "wb_storage": 540.29,
            "wb_acquiring": 558.14,
            "wb_deductions": 2148.00,
            "wb_other": 0.0,
            "source_map": {
                "wb_sale_amount": {"selected_source": "payment_reports.revenue", "selected_value": 14046.08},
                "wb_payout_amount": {"selected_source": "payment_reports.for_pay", "selected_value": 15327.09},
                "wb_total_to_pay": {"selected_source": "payment_reports.missing", "selected_value": None, "source_table": "payment_reports_rows", "source_column": "bank_payment"},
                "wb_logistics": {"selected_source": "payment_reports.missing", "selected_value": None, "source_table": "payment_reports_rows", "source_column": "delivery"},
                "wb_storage": {"selected_source": "payment_reports.missing", "selected_value": None, "source_table": "payment_reports_rows", "source_column": "storage"},
                "wb_acquiring": {"selected_source": "finance_raw_audit.acquiring_fee", "selected_value": 558.14},
                "wb_deductions": {"selected_source": "payment_reports.deduction", "selected_value": 2148.00},
                "wb_other": {"selected_source": "finance_expense_events.other", "selected_value": 0.0},
            },
        },
    )
    monkeypatch.setattr("vooglii_finance.customer_snapshot.get_latest_validation_result", lambda _user_id: None)

    snapshot = build_customer_financial_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot.wb_logistics is None
    assert snapshot.wb_storage is None
    assert snapshot.wb_total_to_pay is None
    assert snapshot.field_trace["wb_logistics"]["selected_source"] == "payment_reports.missing"
    assert snapshot.field_trace["wb_storage"]["selected_source"] == "payment_reports.missing"
    assert snapshot.field_trace["wb_total_to_pay"]["selected_source"] == "payment_reports.missing"
