from __future__ import annotations

from datetime import date

from vooglii_validation.models import WBWeeklyReference
from vooglii_validation import validator


def _reference(**overrides):
    payload = {
        "source_file": "weekly.xlsx",
        "source_hash": "hash-1",
        "period_from": date(2026, 6, 29),
        "period_to": date(2026, 7, 5),
        "report_number": "772098550",
        "revenue": 1000.0,
        "payout": 700.0,
        "logistics": 100.0,
        "storage": 20.0,
        "acquiring": 10.0,
        "wb_deductions": 50.0,
        "other_expenses": 5.0,
        "penalties": 0.0,
        "advertising": 80.0,
        "orders_count": 10,
        "buyouts_count": 8,
        "returns_count": 2,
        "raw_totals": {},
        "metadata": {},
    }
    payload.update(overrides)
    return WBWeeklyReference(**payload)


def test_financial_validation_passes_rounding_delta_within_tolerance(monkeypatch):
    monkeypatch.setattr(
        validator,
        "build_wb_weekly_validation_snapshot",
        lambda *_args, **_kwargs: {
            "wb_sale_amount": 1000.4,
            "wb_payout_amount": 700.0,
            "wb_logistics": 100.0,
            "wb_storage": 20.0,
            "wb_acquiring": 10.0,
            "wb_deductions": 50.0,
            "wb_other": 5.0,
            "penalties": 0.0,
            "advertising": 80.3,
            "orders_count": 10,
            "buyouts_count": 8,
            "returns_count": 2,
            "warnings": [],
            "source_rows": {"finance_raw_audit": 12},
            "source_map": {"advertising": {"selected_source": "finance_expense_events.advertising"}},
        },
    )
    monkeypatch.setattr(
        validator,
        "build_vooglii_validation_snapshot",
        lambda *_args, **_kwargs: {"sales_revenue": 1200.0, "wb_payout": 710.0, "net_profit": 140.0, "finance_confidence": "HIGH"},
    )
    monkeypatch.setattr(validator, "save_validation_result", lambda *_args, **_kwargs: None)

    result = validator.validate_weekly_report(42, _reference())

    assert result.status == "PASS"
    assert result.parity_score == 100.0
    advertising = next(item for item in result.metrics if item.metric == "advertising")
    assert advertising.status == "PASS"


def test_financial_validation_marks_missing_metric_as_insufficient_data(monkeypatch):
    monkeypatch.setattr(
        validator,
        "build_wb_weekly_validation_snapshot",
        lambda *_args, **_kwargs: {
            "wb_sale_amount": 1000.0,
            "wb_payout_amount": 700.0,
            "wb_logistics": None,
            "wb_storage": 20.0,
            "wb_acquiring": 10.0,
            "wb_deductions": 50.0,
            "wb_other": 5.0,
            "penalties": 0.0,
            "advertising": 80.0,
            "orders_count": 10,
            "buyouts_count": 8,
            "returns_count": 2,
            "warnings": [],
            "source_rows": {"finance_raw_audit": 12},
            "source_map": {},
        },
    )
    monkeypatch.setattr(
        validator,
        "build_vooglii_validation_snapshot",
        lambda *_args, **_kwargs: {"sales_revenue": 1200.0, "wb_payout": 710.0, "net_profit": 140.0, "finance_confidence": "HIGH"},
    )
    monkeypatch.setattr(validator, "save_validation_result", lambda *_args, **_kwargs: None)

    result = validator.validate_weekly_report(42, _reference(logistics=None))

    logistics = next(item for item in result.metrics if item.metric == "logistics")
    assert logistics.status == "INSUFFICIENT_DATA"
