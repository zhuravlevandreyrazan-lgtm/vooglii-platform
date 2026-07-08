from __future__ import annotations

import sqlite3
from datetime import date

import config
import db_manager
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "wb-weekly-snapshot.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_wb_weekly_snapshot_keeps_official_only_fields_missing_without_payment_reports(tmp_path, monkeypatch):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) "
            "VALUES('sale-1', 42, '2026-06-30', 'SKU-1', 101, 'BC-1', 1000, 700, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) "
            "VALUES('sale-2', 42, '2026-07-01', 'SKU-1', 101, 'BC-1', 300, -100, 300, 300, 1)"
        )
        conn.execute(
            "INSERT INTO orders(order_id, telegram_id, order_date, supplier_article, nm_id, barcode, total_price, finished_price, price_with_disc, is_cancel) "
            "VALUES('order-1', 42, '2026-06-29', 'SKU-1', 101, 'BC-1', 1200, 1200, 1200, 0)"
        )
        conn.execute(
            "INSERT INTO finance_raw_audit(telegram_id, rrd_id, report_date, deduction, acquiring_fee, penalty, raw_json, created_at) "
            "VALUES(42, 'rrd-1', '2026-06-30', 15, 7, 2, ?, '2026-07-08 10:00:00')",
            ('{"delivery_rub": 80, "storage_fee": 12, "retail_amount": 1500, "ppvz_for_pay": 1100}',),
        )
        conn.execute(
            "INSERT INTO finance_expense_events(user_id, event_date, period_key, source_event_id, source_table, source_type, expense_category, amount, created_at, updated_at) "
            "VALUES(42, '2026-06-30', '2026-06-29..2026-07-05', 'evt-1', 'finance_raw_audit', 'wb_finance', 'advertising', 33, '2026-07-08 10:00:00', '2026-07-08 10:00:00')"
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(
        "vooglii_validation.wb_weekly_snapshot._fetch_payment_snapshot",
        lambda *_args, **_kwargs: {"sales_revenue_total": 1300.0, "sales_for_pay_total": 600.0, "weekly_payout_total_all": 1050.0, "sales_rows_count": 2},
    )

    snapshot = build_wb_weekly_snapshot(42, date(2026, 6, 29), date(2026, 7, 5))

    assert snapshot.wb_logistics is None
    assert snapshot.wb_storage is None
    assert snapshot.wb_total_to_pay is None
    assert snapshot.wb_acquiring == 7.0
    assert snapshot.wb_deductions == 15.0
    assert snapshot.penalties == 2.0
    assert snapshot.advertising == 33.0
    assert snapshot.wb_sale_amount == 1500.0
    assert snapshot.wb_payout_amount == 1100.0
    assert snapshot.orders_count == 1
    assert snapshot.buyouts_count == 1
    assert snapshot.returns_count == 1
    assert snapshot.source_map["wb_logistics"]["selected_source"] == "payment_reports.missing"
    assert snapshot.source_map["wb_storage"]["selected_source"] == "payment_reports.missing"
    assert snapshot.source_map["wb_total_to_pay"]["selected_source"] == "payment_reports.missing"
