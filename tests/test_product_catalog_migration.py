from __future__ import annotations

import sqlite3

import config
import db_manager
import product_catalog


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "product-catalog-migration.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    product_catalog.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_legacy_cost_migration_resolves_unique_nm_id(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(telegram_id, username, tariff, is_active) VALUES(42, 'u', 'PRO', 1)")
        conn.execute("INSERT INTO products(telegram_id, supplier_article, cost_price, last_price) VALUES(42, 'SKU-1', 123, 999)")
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'SKU-1', 101, 'BC-1', 1000, 800, 1000, 1000, 0)"
        )
        conn.commit()
    finally:
        conn.close()

    result = product_catalog.migrate_legacy_products(42)
    assert result["warnings"] == []

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT user_id, nm_id, supplier_article, cost_price, last_price, source FROM product_catalog WHERE user_id=42"
        ).fetchone()
    finally:
        conn.close()

    assert row == (42, 101, "SKU-1", 123.0, 999.0, "legacy_products_resolved")


def test_legacy_cost_migration_keeps_cost_with_synthetic_nm_id_when_ambiguous(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(telegram_id, username, tariff, is_active) VALUES(42, 'u', 'PRO', 1)")
        conn.execute("INSERT INTO products(telegram_id, supplier_article, cost_price, last_price) VALUES(42, 'SKU-X', 50, 200)")
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'SKU-X', 101, 'BC-1', 1000, 800, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO orders(order_id, telegram_id, order_date, supplier_article, nm_id, barcode, total_price, finished_price, price_with_disc, is_cancel, cancel_date) VALUES('order-1', 42, '2026-05-11', 'SKU-X', 202, 'BC-2', 1200, 1200, 1200, 0, NULL)"
        )
        conn.commit()
    finally:
        conn.close()

    result = product_catalog.migrate_legacy_products(42)
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["reason"] == "multiple_nm_id_candidates"

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT nm_id, supplier_article, cost_price, source FROM product_catalog WHERE user_id=42"
        ).fetchone()
    finally:
        conn.close()

    assert row[0] < 0
    assert row[1:] == ("SKU-X", 50.0, "legacy_products_unresolved")
