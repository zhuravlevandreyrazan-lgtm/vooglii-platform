from __future__ import annotations

import sqlite3

import config
import db_manager
import product_catalog
import report
import user_manager


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "cost-matching-v2.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    product_catalog.DB_NAME = db_path
    report.DB_NAME = db_path
    user_manager.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_cost_matching_priority_nm_id_then_supplier_article_then_barcode(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users(telegram_id, username, tariff, is_active, subscription_until) VALUES(42, 'u', 'PRO', 1, '2026-12-31')"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'SKU-NM', 101, 'BC-NM', 1000, 800, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-2', 42, '2026-05-11', 'SKU-ARTICLE', 999, 'BC-A', 2000, 1700, 2000, 2000, 0)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-3', 42, '2026-05-12', 'SKU-OTHER', 998, 'BC-BAR', 3000, 2600, 3000, 3000, 0)"
        )
        conn.execute(
            "INSERT INTO product_catalog(user_id, nm_id, supplier_article, barcode, cost_price, last_price, source, created_at, updated_at) VALUES(42, 101, 'SKU-NM', 'BC-NM', 20, 1000, 'test', '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO product_catalog(user_id, nm_id, supplier_article, barcode, cost_price, last_price, source, created_at, updated_at) VALUES(42, 202, 'SKU-ARTICLE', 'BC-A-OTHER', 30, 2000, 'test', '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.execute(
            "INSERT INTO product_catalog(user_id, nm_id, supplier_article, barcode, cost_price, last_price, source, created_at, updated_at) VALUES(42, 303, 'SKU-BAR', 'BC-BAR', 40, 3000, 'test', '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.commit()
    finally:
        conn.close()

    stats = report.get_profit_stats(("2026-05-01", "2026-05-31"), 42)
    coverage = report.get_cost_fill_stats(("2026-05-01", "2026-05-31"), 42)

    assert float(stats[3]) == 90.0
    assert coverage["total_rows"] == 3
    assert coverage["rows_with_cost"] == 3
    assert coverage["missing_articles"] == 0
