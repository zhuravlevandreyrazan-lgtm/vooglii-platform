from __future__ import annotations

import sqlite3
from datetime import date

import config
import db_manager
from vooglii_finance.customer_snapshot import PERIOD_CLOSED, PERIOD_OPEN, refresh_wb_financial_period


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "wb-periods.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_wb_financial_period_marks_closed_for_past_week_with_finance_rows(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO finance_raw_audit(telegram_id, rrd_id, report_date, deduction, raw_json, created_at) VALUES(42, 'rrd-1', '2026-06-30', 10, '{}', '2026-07-08 10:00:00')"
        )
        conn.commit()
    finally:
        conn.close()

    period = refresh_wb_financial_period(42, date(2026, 6, 29), date(2026, 7, 5))

    assert period["status"] == PERIOD_CLOSED


def test_wb_financial_period_marks_open_for_current_period_without_rows(tmp_path):
    _prepare_db(tmp_path)

    period = refresh_wb_financial_period(42, date.today().replace(day=max(1, date.today().day - 1)), date.today())

    assert period["status"] == PERIOD_OPEN
