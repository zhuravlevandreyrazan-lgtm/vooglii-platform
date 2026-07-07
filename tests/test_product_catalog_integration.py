from __future__ import annotations

import asyncio
import importlib.util
import sqlite3
from pathlib import Path

import config
import db_manager
import product_catalog


def _load_module(module_name: str, relative_path: str):
    path = Path(__file__).resolve().parent.parent / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _prepare_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "product-catalog-integration.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    product_catalog.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_update_style_sync_populates_catalog_and_preserves_manual_cost(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(telegram_id, username, tariff, is_active) VALUES(42, 'u', 'PRO', 1)")
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'SKU-1', 101, 'BC-1', 1000, 800, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-2', 42, '2026-05-11', 'SKU-2', 202, 'BC-2', 2000, 1600, 2000, 2000, 0)"
        )
        conn.execute(
            "INSERT INTO stocks(unique_key, telegram_id, stock_date, supplier_article, nm_id, barcode, warehouse_name, quantity, quantity_full, in_way_to_client, in_way_from_client) VALUES('stock-1', 42, '2026-05-10', 'SKU-1', 101, 'BC-1', 'WH', 7, 7, 0, 0)"
        )
        conn.execute(
            "INSERT INTO advertising(unique_key, telegram_id, advert_date, campaign_id, supplier_article, nm_id, app_type, name, spend, sum_price) VALUES('adv-1', 42, '2026-05-10', '11', 'SKU-1', 101, 'search', 'SKU-1 name', 100, 900)"
        )
        conn.commit()
    finally:
        conn.close()

    first = product_catalog.sync_product_catalog(42, period=("2026-05-01", "2026-05-31"))
    assert first["source_rows"] >= 2
    assert first["status"] == product_catalog.CATALOG_SYNC_MISSING_COST_VALUES

    manual = product_catalog.set_cost_price("101", 123, user_id=42)
    assert manual["nm_id"] == 101

    second = product_catalog.sync_product_catalog(42, period=("2026-05-01", "2026-05-31"))
    audit = product_catalog.build_product_catalog_audit(42, period=("2026-05-01", "2026-05-31"))

    assert second["meta"]["coverage_percent"] == 50.0
    assert audit["catalog_rows"] >= 2
    assert audit["rows_with_cost"] == 1
    assert audit["matched_by_nm_id"] == 1
    assert audit["matched_by_supplier_article"] == 0
    assert audit["matched_by_barcode"] == 0
    assert audit["matched_by_legacy_fallback"] == 0
    assert any(row["supplier_article"] == "SKU-2" for row in audit["top_missing_cost"])

    matched = product_catalog.match_product(42, nm_id=101)
    assert matched is not None
    assert float(matched["cost_price"]) == 123.0


def test_diagnostics_use_product_catalog_as_primary_source(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(telegram_id, username, tariff, is_active) VALUES(42, 'u', 'PRO', 1)")
        conn.execute(
            "INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, total_price, for_pay, finished_price, price_with_disc, is_return) VALUES('sale-1', 42, '2026-05-10', 'SKU-A', 111, 'BC-A', 1000, 800, 1000, 1000, 0)"
        )
        conn.execute(
            "INSERT INTO products(telegram_id, supplier_article, cost_price, last_price) VALUES(42, 'SKU-A', 777, 1000)"
        )
        conn.execute(
            "INSERT INTO product_catalog(user_id, nm_id, supplier_article, barcode, cost_price, last_price, source, created_at, updated_at) VALUES(42, 111, 'SKU-A', 'BC-A', 55, 1000, 'test', '2026-07-07 12:00:00', '2026-07-07 12:00:00')"
        )
        conn.commit()
    finally:
        conn.close()

    audit_module = _load_module("audit_wb_data_loading_integration_test", "scripts/audit_wb_data_loading.py")
    audit = audit_module.build_wb_data_loading_audit(42, "2026-05-01", "2026-05-31", db_path=db_path)

    assert audit["products"]["rows_count"] == 1
    assert audit["products"]["rows_with_cost"] == 1
    assert audit["cost_audit"]["coverage_percent"] == 100.0
    assert audit["cost_audit"]["matched_by_nm_id"] == 1
    assert audit["cost_audit"]["matched_by_legacy_fallback"] == 0
    assert any("product_catalog" in item for item in audit["conclusions"])
