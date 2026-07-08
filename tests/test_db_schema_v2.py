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
    import scripts.audit_db_schema_v2 as audit_db_schema_v2

    importlib.reload(config)
    importlib.reload(db_manager)
    importlib.reload(audit_db_schema_v2)
    return config, db_manager, audit_db_schema_v2


def test_schema_v2_tables_and_indexes_exist():
    with tempfile.TemporaryDirectory() as tmp_dir:
        _config, db_manager, audit_db_schema_v2 = _reload_modules(tmp_dir)
        db_manager.init_db()
        report = audit_db_schema_v2.audit_schema()

        assert report["is_compatible"] is True
        for table_name in (
            "sync_state",
            "finance_expense_events",
            "payment_reports_rows",
            "stock_snapshots",
            "financial_snapshot_audit",
        ):
            assert table_name in report["table_names"]
        for index_name in (
            "idx_finance_expense_events_user_date",
            "idx_payment_reports_rows_user_period",
            "idx_stock_snapshots_user_date",
            "idx_financial_snapshot_audit_user_period",
        ):
            assert index_name in report["index_names"]


def test_old_db_is_migrated_without_losing_rows():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, db_manager, audit_db_schema_v2 = _reload_modules(tmp_dir)
        db_path = Path(config.DB_NAME)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE sales(
                sale_id TEXT PRIMARY KEY,
                telegram_id INTEGER,
                sale_date TEXT,
                supplier_article TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sales(sale_id, telegram_id, sale_date, supplier_article)
            VALUES('sale-1', 42, '2026-06-10', 'SKU-1')
            """
        )
        conn.commit()
        conn.close()

        db_manager.init_db()

        conn = sqlite3.connect(str(db_path))
        row = conn.execute("SELECT sale_id, telegram_id, sale_date, supplier_article FROM sales").fetchone()
        conn.close()
        report = audit_db_schema_v2.audit_schema()

        assert row == ("sale-1", 42, "2026-06-10", "SKU-1")
        assert report["is_compatible"] is True
        assert report["compatibility"]["sales"]["user_scope_column"] == "telegram_id"


if __name__ == "__main__":
    test_schema_v2_tables_and_indexes_exist()
    test_old_db_is_migrated_without_losing_rows()
    print("DB SCHEMA V2 OK", flush=True)
