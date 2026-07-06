from __future__ import annotations

import sqlite3

import config
import db_manager
import report
import telegram_bot
import vooglii_telegram.legacy_bot as legacy_bot
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


TEST_USER_ID = 658486226
TEST_DAYS = ("2026-05-01", "2026-05-31")


def _patch_db(monkeypatch, tmp_path):
    db_path = tmp_path / "may_live_style.db"
    db_name = str(db_path)
    for module in (config, db_manager, report, telegram_bot, legacy_bot):
        monkeypatch.setattr(module, "DB_NAME", db_name, raising=False)
    db_manager.init_db()
    return db_name


def test_unified_snapshot_stays_non_zero_when_live_may_rows_exist(monkeypatch, tmp_path):
    db_name = _patch_db(monkeypatch, tmp_path)
    monkeypatch.setattr(report, "is_pro", lambda _telegram_id: True)

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sales(sale_id,telegram_id,sale_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,for_pay,finished_price,price_with_disc,is_return) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("sale-1", TEST_USER_ID, "2026-05-15", "SKU-1", 101, "B1", "WH", "Cat", "Brand", 10000.0, 8000.0, 10000.0, 10000.0, 0),
    )
    cur.execute(
        "INSERT INTO sales(sale_id,telegram_id,sale_date,supplier_article,nm_id,barcode,warehouse_name,category,brand,total_price,for_pay,finished_price,price_with_disc,is_return) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("sale-2", TEST_USER_ID, "2026-05-20", "SKU-2", 102, "B2", "WH", "Cat", "Brand", 6000.0, 4500.0, 6000.0, 6000.0, 0),
    )
    cur.execute(
        "INSERT INTO products(telegram_id,supplier_article,cost_price,last_price) VALUES(?,?,?,?)",
        (TEST_USER_ID, "SKU-1", 3000.0, 10000.0),
    )
    cur.execute(
        "INSERT INTO products(telegram_id,supplier_article,cost_price,last_price) VALUES(?,?,?,?)",
        (TEST_USER_ID, "SKU-2", 2000.0, 6000.0),
    )
    cur.execute(
        "INSERT INTO advertising(unique_key,telegram_id,advert_date,campaign_id,campaign_name,supplier_article,nm_id,views,clicks,orders,sum_price,spend,ctr,cpc,cr) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("ads-1", TEST_USER_ID, "2026-05-18", "CAMP-1", "May campaign", "SKU-1", 101, 1000, 50, 4, 9000.0, 1500.0, 5.0, 30.0, 8.0),
    )
    cur.execute(
        "INSERT INTO expenses(unique_key,telegram_id,expense_date,expense_type,amount,supplier_article,comment,source,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        ("exp-logi", TEST_USER_ID, "2026-05-18", "logistics", 700.0, None, "manual", "manual", "2026-05-18 10:00:00"),
    )
    cur.execute(
        "INSERT INTO expenses(unique_key,telegram_id,expense_date,expense_type,amount,supplier_article,comment,source,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        ("exp-stor", TEST_USER_ID, "2026-05-19", "storage", 250.0, None, "manual", "manual", "2026-05-19 10:00:00"),
    )
    cur.execute(
        "INSERT INTO expenses(unique_key,telegram_id,expense_date,expense_type,amount,supplier_article,comment,source,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        ("exp-other", TEST_USER_ID, "2026-05-19", "other", 125.0, None, "manual", "manual", "2026-05-19 10:00:00"),
    )
    cur.execute(
        "INSERT INTO finance_raw_audit(telegram_id,rrd_id,report_date,deduction,acquiring_fee,penalty,acceptance,acceptance_fee,additional_payment,nm_id,supplier_article,raw_json,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (TEST_USER_ID, "rrd-1", "2026-05-21", 420.0, 180.0, 50.0, 30.0, 20.0, 10.0, "101", "SKU-1", "{}", "2026-05-21 10:00:00"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": 12500.0,
            "sales_for_pay_total": 12500.0,
            "sales_revenue_total": 16000.0,
            "payment_reports_source": "diagnostic_fixture",
            "payment_reports_status": "OK",
            "payment_reports_count": 1,
        },
    )
    monkeypatch.setattr(
        legacy_bot,
        "_payment_reconciliation_snapshot",
        telegram_bot._payment_reconciliation_snapshot,
    )
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "WAITING"})
    monkeypatch.setattr(legacy_bot, "_finance_api_status_snapshot", telegram_bot._finance_api_status_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": False,
            "status": "UNAVAILABLE",
            "official_net_profit": None,
        },
    )
    monkeypatch.setattr(legacy_bot, "_financial_engine_snapshot", telegram_bot._financial_engine_snapshot)

    snapshot = build_unified_financial_snapshot_dict(TEST_USER_ID, TEST_DAYS, bot=telegram_bot)

    assert snapshot["sales_revenue"] == 16000.0
    assert snapshot["wb_payout"] == 12500.0
    assert snapshot["cost_price"] == 5000.0
    assert snapshot["advertising_spend"] == 1500.0
    assert snapshot["logistics"] == 700.0
    assert snapshot["storage"] == 250.0
    assert snapshot["acquiring"] == 180.0
    assert snapshot["wb_deductions"] == 420.0
    assert snapshot["other_expenses"] == 125.0
    assert snapshot["unknown_wb_expenses"] is None or snapshot["unknown_wb_expenses"] >= 0
    assert snapshot["customer_unknown_wb_expenses"] is None or snapshot["customer_unknown_wb_expenses"] >= 0
    assert snapshot["cost_status"] in ("COST_OK", "COST_PARTIAL")
