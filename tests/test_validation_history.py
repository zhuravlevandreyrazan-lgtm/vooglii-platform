from __future__ import annotations

import sqlite3
from datetime import date

import config
import db_manager
from vooglii_validation.models import ValidationResult, WBWeeklyReference
from vooglii_validation.validator import get_latest_validation_result, list_validation_history, save_validation_result


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "validation-history.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_validation_history_is_saved_and_listed(tmp_path):
    db_path = _prepare_db(tmp_path)
    reference = WBWeeklyReference(
        source_file="weekly.xlsx",
        source_hash="hash-1",
        period_from=date(2026, 6, 29),
        period_to=date(2026, 7, 5),
        report_number="772098550",
        revenue=1000.0,
        payout=700.0,
        logistics=100.0,
        storage=20.0,
        acquiring=10.0,
        wb_deductions=50.0,
        other_expenses=5.0,
        penalties=0.0,
        advertising=80.0,
        orders_count=10,
        buyouts_count=8,
        returns_count=2,
        raw_totals={},
        metadata={},
    )
    result = ValidationResult(
        user_id=42,
        period_from=date(2026, 6, 29),
        period_to=date(2026, 7, 5),
        reference_hash="hash-1",
        parity_score=99.7,
        metrics=[],
        failed_metrics=["advertising"],
        warnings=["warn"],
        status="WARN",
    )

    save_validation_result(reference, result)

    rows = list_validation_history(42)
    latest = get_latest_validation_result(42)

    assert rows
    assert rows[0]["reference_hash"] == "hash-1"
    assert rows[0]["failed_metrics"] == ["advertising"]
    assert latest is not None and latest["status"] == "WARN"
