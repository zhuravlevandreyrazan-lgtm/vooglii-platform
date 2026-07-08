from __future__ import annotations

import sqlite3
from datetime import date

import config
import db_manager
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "wb-native-weekly-mapping.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_wb_native_weekly_mapping_prefers_weekly_report_totals(tmp_path, monkeypatch):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO finance_raw_audit(telegram_id, rrd_id, report_date, deduction, acquiring_fee, raw_json, created_at) "
            "VALUES(42, 'rrd-1', '2026-06-30', 2148.00, 558.14, ?, '2026-07-08 10:00:00')",
            ('{"delivery_rub": 3613.80, "storage_fee": 540.29, "retail_amount": 37624.19, "ppvz_for_pay": 15327.09}',),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(
        "vooglii_validation.wb_weekly_snapshot._fetch_payment_snapshot",
        lambda *_args, **_kwargs: {
            "payment_reports_rows": [
                {
                    "period_start": "2026-06-29",
                    "period_end": "2026-07-05",
                    "type": "main",
                    "revenue": 14046.08,
                    "for_pay": 15327.09,
                    "bank_payment": 9084.94,
                    "delivery": 3463.06,
                    "storage": 631.09,
                    "deduction": 2148.00,
                }
            ],
            "payment_reports_total_revenue": 0.0,
            "payment_reports_total_for_pay": 0.0,
            "payment_reports_total_bank_payment": 0.0,
            "payment_reports_total_delivery": 0.0,
            "payment_reports_total_storage": 0.0,
            "payment_reports_total_deduction": 0.0,
            "weekly_payout_total_all": 15327.09,
        },
    )

    snapshot = build_wb_weekly_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot.wb_sale_amount == 14046.08
    assert snapshot.wb_payout_amount == 15327.09
    assert snapshot.wb_logistics == 3463.06
    assert snapshot.wb_storage == 631.09
    assert snapshot.wb_acquiring == 558.14
    assert snapshot.wb_deductions == 2148.00
    assert snapshot.wb_total_to_pay == 9084.94
    assert snapshot.source_map["wb_sale_amount"]["selected_source"] == "payment_reports.revenue"
    assert snapshot.source_map["wb_logistics"]["source_table"] == "payment_reports_rows"
    assert snapshot.source_map["wb_storage"]["source_column"] == "storage"
    assert snapshot.source_map["wb_total_to_pay"]["selected_source"] == "payment_reports.bank_payment"
    assert snapshot.source_map["wb_total_to_pay"]["source_column"] == "bank_payment"
