from __future__ import annotations

from datetime import date

from vooglii_validation.models import WBWeeklyReference
from vooglii_validation.root_cause import infer_root_cause
from vooglii_validation import validator


def _reference(**overrides):
    payload = {
        "source_file": "weekly.xlsx",
        "source_hash": "hash-2",
        "period_from": date(2026, 6, 29),
        "period_to": date(2026, 7, 5),
        "report_number": "772098550",
        "revenue": 1500.0,
        "payout": 1100.0,
        "logistics": 80.0,
        "storage": 12.0,
        "acquiring": 7.0,
        "wb_deductions": 15.0,
        "other_expenses": 2.0,
        "penalties": 2.0,
        "advertising": 33.0,
        "orders_count": 1,
        "buyouts_count": 1,
        "returns_count": 1,
        "raw_totals": {},
        "metadata": {},
    }
    payload.update(overrides)
    return WBWeeklyReference(**payload)


def test_weekly_parity_validator_uses_weekly_snapshot_not_management_snapshot(monkeypatch):
    monkeypatch.setattr(
        validator,
        "build_wb_weekly_validation_snapshot",
        lambda *_args, **_kwargs: {
            "wb_sale_amount": 1500.0,
            "wb_payout_amount": 1100.0,
            "wb_logistics": 80.0,
            "wb_storage": 12.0,
            "wb_acquiring": 7.0,
            "wb_deductions": 15.0,
            "wb_other": 2.0,
            "penalties": 2.0,
            "advertising": 33.0,
            "orders_count": 1,
            "buyouts_count": 1,
            "returns_count": 1,
            "warnings": [],
            "source_rows": {"finance_raw_audit": 10},
            "source_map": {"wb_sale_amount": {"selected_source": "finance_raw_audit.raw_json"}},
        },
    )
    monkeypatch.setattr(
        validator,
        "build_vooglii_validation_snapshot",
        lambda *_args, **_kwargs: {
            "sales_revenue": 9000.0,
            "wb_payout": 5000.0,
            "net_profit": 3000.0,
            "finance_confidence": "LOW",
        },
    )
    monkeypatch.setattr(validator, "save_validation_result", lambda *_args, **_kwargs: None)

    result = validator.validate_weekly_report(42, _reference())

    assert result.status == "PASS"
    assert result.parity_score == 100.0
    assert result.management_context["sales_revenue"] == 9000.0
    assert "management p&l" in " ".join(result.warnings).lower()


def test_root_cause_model_mismatch_is_explicit():
    cause = infer_root_cause(
        "revenue",
        1500.0,
        1800.0,
        {"source_rows": {"finance_raw_audit": 10}, "source_map": {"wb_sale_amount": {"selected_source": "payment_reconciliation.sales_revenue_total"}}},
    )

    assert cause == "model_mismatch_management_vs_wb_weekly"
