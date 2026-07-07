import sqlite3
from datetime import datetime
from config import DB_NAME
from db_manager import init_db
from product_catalog import (
    build_product_catalog_audit,
    get_cost_map as get_catalog_cost_map,
    get_cost_price as get_catalog_cost_price,
    list_catalog_products,
    set_cost_price as set_catalog_cost_price,
    sync_product_catalog,
)


def _conn(): init_db(); return sqlite3.connect(DB_NAME)

def set_cost_price(article, cost_price, telegram_id=None):
    tid=telegram_id or 0
    return set_catalog_cost_price(article, float(cost_price), user_id=tid)

def get_cost_price(article, telegram_id=None):
    raw = str(article or "").strip()
    try:
        nm_id = int(raw)
    except Exception:
        nm_id = None
    return get_catalog_cost_price(telegram_id or 0, nm_id=nm_id, supplier_article=None if nm_id is not None else raw, barcode=None if nm_id is not None else raw)

def get_products(telegram_id=None):
    rows = list_catalog_products(telegram_id or 0, with_cost_only=True)
    return [
        ((row.get("supplier_article") or str(row.get("nm_id") or "-")), float(row.get("cost_price") or 0))
        for row in rows
    ]

def sync_products_from_sales(telegram_id=None):
    sync_product_catalog(telegram_id or 0)


def get_product_catalog_audit(telegram_id=None, period=None):
    return build_product_catalog_audit(telegram_id or 0, period=period)
