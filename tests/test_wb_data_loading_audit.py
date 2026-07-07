from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import config
import db_manager


def _load_module(module_name: str, relative_path: str):
    path = Path(__file__).resolve().parent.parent / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _prepare_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "audit.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_scope_report_detects_missing_token_and_empty_scopes(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO users(telegram_id, username, wb_token, tariff, is_active)
            VALUES(658486226, 'tester', '', 'PRO', 1)
            """
        )
        conn.commit()
    finally:
        conn.close()

    module = _load_module("check_wb_token_scopes_test", "scripts/check_wb_token_scopes.py")
    report = module.build_scope_report(658486226, db_path=db_path)

    assert report["resolved_source"] == "missing"
    assert report["users_token_present"] is False
    assert report["wb_cabinets_rows"] == []
    assert any("live WB sync cannot run" in note for note in report["notes"])


def test_data_loading_audit_detects_finance_wider_than_sales_and_period_window_mismatch(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users(telegram_id, username, wb_token, tariff, is_active) VALUES(658486226, 'tester', '', 'PRO', 1)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 658486226, '2026-05-10', 'SKU-1', 101, 'BC-1', 1200, 900, 1200, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO advertising(unique_key, telegram_id, advert_date, campaign_id, supplier_article, nm_id, spend, sum_price) VALUES('adv-1', 658486226, '2026-05-10', '11', 'SKU-1', 101, 120.5, 900)"
        )
        conn.execute(
            "INSERT INTO expenses(unique_key, telegram_id, expense_date, expense_type, amount, supplier_article, source, created_at) VALUES('exp-1', 658486226, '2026-05-10', 'logistics', 80, 'SKU-1', 'api_finance', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO finance_raw_audit(telegram_id, rrd_id, report_date, deduction, acquiring_fee, created_at) VALUES(658486226, 'rrd-1', '2026-05-13', 15, 7, '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO finance_expense_events(user_id, event_date, period_key, source_event_id, source_table, source_type, expense_category, amount, created_at, updated_at) VALUES(658486226, '2026-05-10', '2026-05-01..2026-05-31', 'advertising:adv-1', 'advertising', 'selected_source', 'advertising', 120.5, '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO finance_expense_events(user_id, event_date, period_key, source_event_id, source_table, source_type, expense_category, amount, created_at, updated_at) VALUES(658486226, '2026-05-10', '2026-05-01..2026-05-31', 'expense:exp-1', 'expenses', 'api_finance', 'logistics', 80, '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO finance_expense_events(user_id, event_date, period_key, source_event_id, source_table, source_type, expense_category, amount, created_at, updated_at) VALUES(658486226, '2026-05-13', '2026-05-01..2026-05-31', 'finance_raw:1:wb_deductions', 'finance_raw_audit', 'wb_finance', 'wb_deductions', 15, '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO finance_expense_events(user_id, event_date, period_key, source_event_id, source_table, source_type, expense_category, amount, created_at, updated_at) VALUES(658486226, '2026-05-13', '2026-05-01..2026-05-31', 'finance_raw:1:acquiring', 'finance_raw_audit', 'wb_finance', 'acquiring', 7, '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO products(telegram_id, supplier_article, cost_price, last_price) VALUES(658486226, 'SKU-1', 250, 1000)"
        )
        conn.commit()
    finally:
        conn.close()

    module = _load_module("audit_wb_data_loading_test", "scripts/audit_wb_data_loading.py")
    audit = module.build_wb_data_loading_audit(658486226, "2026-05-01", "2026-05-31", db_path=db_path)

    assert audit["sync_state"]["sales"]["status"] == "MISSING"
    assert audit["tables"]["sales"]["rows_count"] == 1
    assert audit["tables"]["finance_expense_events"]["rows_count"] == 4
    assert audit["cost_audit"]["coverage_percent"] == 100.0
    assert audit["period_window_check"]["sales_period_rows"] == 1
    assert audit["period_window_check"]["sales_rolling_rows"] == 0
    assert any("finance_expense_events is wider" in item for item in audit["conclusions"])
    assert any("period-aware" in item for item in audit["conclusions"])
