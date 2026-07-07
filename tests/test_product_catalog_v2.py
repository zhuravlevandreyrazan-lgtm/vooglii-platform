from __future__ import annotations

import sqlite3

import config
import db_manager
import product_catalog


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "product-catalog-v2.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    product_catalog.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_catalog_auto_enrich_and_preserve_manual_cost(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(telegram_id, username, tariff, is_active) VALUES(42, 'u', 'PRO', 1)")
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, brand, category, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'SKU-1', 101, 'BC-1', 'Brand A', 'Subject A', 1000, 800, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO orders(order_id, telegram_id, order_date, supplier_article, nm_id, barcode, brand, category, total_price, finished_price, price_with_disc, is_cancel, cancel_date) VALUES('order-1', 42, '2026-05-10', 'SKU-1', 101, 'BC-1', 'Brand A', 'Subject A', 1000, 1000, 1000, 0, NULL)"
        )
        conn.execute(
            "INSERT INTO stocks(unique_key, telegram_id, stock_date, supplier_article, nm_id, barcode, warehouse_name, quantity, quantity_full, in_way_to_client, in_way_from_client) VALUES('stock-1', 42, '2026-05-10', 'SKU-1', 101, 'BC-1', 'WH', 10, 10, 0, 0)"
        )
        conn.execute(
            "INSERT INTO advertising(unique_key, telegram_id, advert_date, campaign_id, supplier_article, nm_id, app_type, name, spend, sum_price) VALUES('adv-1', 42, '2026-05-10', '11', 'SKU-1', 101, 'search', 'Product Name', 100, 700)"
        )
        conn.commit()
    finally:
        conn.close()

    sync_first = product_catalog.sync_product_catalog(42, period=("2026-05-01", "2026-05-31"))
    assert sync_first["inserted"] >= 1

    row = product_catalog.match_product(42, nm_id=101)
    assert row is not None
    assert row["supplier_article"] == "SKU-1"
    assert row["barcode"] == "BC-1"
    assert row["brand"] == "Brand A"
    assert row["subject"] == "Subject A"

    product_catalog.set_cost_price("SKU-1", 55, user_id=42)
    sync_second = product_catalog.sync_product_catalog(42, period=("2026-05-01", "2026-05-31"))
    assert sync_second["meta"]["coverage_percent"] == 100.0

    row_after = product_catalog.match_product(42, nm_id=101)
    assert row_after is not None
    assert float(row_after["cost_price"]) == 55.0
    audit = product_catalog.build_product_catalog_audit(42, period=("2026-05-01", "2026-05-31"))
    assert audit["coverage_percent"] == 100.0
    assert audit["missing_cost_skus"] == 0
