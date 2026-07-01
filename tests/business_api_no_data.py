from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import api_server
import telegram_bot
from analytics import business as business_module
from analytics.cache import invalidate_cache


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _build_empty_db() -> str:
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    conn = sqlite3.connect(handle.name)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE sales (
            telegram_id INTEGER,
            sale_date TEXT,
            is_return INTEGER,
            price_with_disc REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE orders (
            telegram_id INTEGER,
            order_date TEXT,
            is_cancel INTEGER,
            order_id TEXT,
            price_with_disc REAL
        )
        """
    )
    conn.commit()
    conn.close()
    return handle.name


def run_check() -> None:
    empty_db_path = _build_empty_db()
    client = TestClient(api_server.app)

    original_db_name = business_module.DB_NAME
    original_report = telegram_bot._report_mgmt_snapshot
    original_metrics = telegram_bot._business_metrics_snapshot
    original_director = telegram_bot._director_snapshot
    original_sku = telegram_bot._sku_analytics_rows

    try:
        business_module.DB_NAME = empty_db_path
        telegram_bot._report_mgmt_snapshot = lambda *args, **kwargs: {
            "revenue": 0.0,
            "management_profit": 0.0,
            "management_profit_with_storage": 0.0,
            "management_margin": 0.0,
            "recommended_profit": 0.0,
        }
        telegram_bot._business_metrics_snapshot = lambda *args, **kwargs: {
            "operational_revenue": 0.0,
            "operational_net_profit": 0.0,
            "official_net_profit": 0.0,
            "legacy_financial_profit_estimate": 0.0,
        }
        telegram_bot._director_snapshot = lambda *args, **kwargs: {"business_health": "UNKNOWN"}
        telegram_bot._sku_analytics_rows = lambda *args, **kwargs: ([], None)

        invalidate_cache("business")
        response = client.get("/api/business")
        payload = response.json()

        _assert(response.status_code == 200, "/api/business should return 200 for empty SQLite")
        _assert((payload.get("runtime") or {}).get("source") == "live", "empty SQLite test should exercise live builder")
        _assert(payload.get("summary", {}).get("revenue") is None, "summary.revenue should be null for empty SQLite")
        _assert(payload.get("summary", {}).get("profit") is None, "summary.profit should be null for empty SQLite")
        _assert(payload.get("summary", {}).get("orders") is None, "summary.orders should be null for empty SQLite")
        _assert(payload.get("healthStatus") == "No business data available", "healthStatus should report no business data")
    finally:
        invalidate_cache("business")
        business_module.DB_NAME = original_db_name
        telegram_bot._report_mgmt_snapshot = original_report
        telegram_bot._business_metrics_snapshot = original_metrics
        telegram_bot._director_snapshot = original_director
        telegram_bot._sku_analytics_rows = original_sku
        try:
            Path(empty_db_path).unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    run_check()
    print("BUSINESS API NO-DATA CHECK OK", flush=True)
