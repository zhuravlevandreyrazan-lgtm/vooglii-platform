from __future__ import annotations

import importlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_modules(tmp_dir: str):
    os.environ["DB_DIR"] = tmp_dir
    import config
    import db_manager
    import vooglii_wb_sync.stocks_loader as stocks_loader

    importlib.reload(config)
    importlib.reload(db_manager)
    importlib.reload(stocks_loader)
    return config, db_manager, stocks_loader


def test_sync_stocks_writes_stock_snapshots(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, db_manager, stocks_loader = _reload_modules(tmp_dir)
        db_manager.init_db()

        def _fake_load_stocks(user_id, _token):
            conn = sqlite3.connect(config.DB_NAME)
            conn.execute(
                """
                INSERT INTO stocks(unique_key, telegram_id, stock_date, supplier_article, nm_id, barcode, warehouse_name, quantity, quantity_full, in_way_to_client, in_way_from_client)
                VALUES('stock-1', ?, '2026-07-07', 'SKU-1', 1001, 'bc', 'WH', 5, 5, 0, 0)
                """,
                (int(user_id),),
            )
            conn.commit()
            conn.close()
            return 1, "SUCCESS"

        monkeypatch.setattr(stocks_loader.load_sales, "load_stocks", _fake_load_stocks)

        payload = stocks_loader.sync_stocks(42, "token", 30)

        conn = sqlite3.connect(config.DB_NAME)
        rows = conn.execute("SELECT COUNT(*) FROM stock_snapshots WHERE user_id=42").fetchone()[0]
        conn.close()

        assert payload["raw_status"] == "SUCCESS"
        assert payload["meta"]["stock_snapshots_bridge"]["status"] == "OK"
        assert rows == 1


if __name__ == "__main__":
    test_sync_stocks_writes_stock_snapshots(__import__("pytest").MonkeyPatch())
    print("STOCK SNAPSHOTS BRIDGE OK", flush=True)
