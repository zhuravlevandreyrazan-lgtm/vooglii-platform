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
    import vooglii_finance.bridges as bridges

    importlib.reload(config)
    importlib.reload(db_manager)
    importlib.reload(bridges)
    return config, db_manager, bridges


def test_other_expenses_from_legacy_api_finance_are_traceable_but_not_confirmed():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, db_manager, bridges = _reload_modules(tmp_dir)
        db_manager.init_db()
        conn = sqlite3.connect(config.DB_NAME)
        conn.execute(
            "INSERT INTO expenses(unique_key, telegram_id, expense_date, expense_type, amount, source, created_at) "
            "VALUES('exp-other', 42, '2026-05-11', 'other', 97.61, 'api_finance', '2026-05-11 10:00:00')"
        )
        conn.execute(
            "INSERT INTO advertising(unique_key, telegram_id, advert_date, campaign_id, spend) "
            "VALUES('adv-1', 42, '2026-05-11', '11', 110.44)"
        )
        conn.commit()
        conn.close()

        bridges.normalize_finance_expense_events(42, "2026-05-01", "2026-05-31")
        trace_rows = bridges.get_finance_expense_event_trace(42, "2026-05-01", "2026-05-31", "other")
        integrity = bridges.build_finance_source_integrity_report(42, "2026-05-01", "2026-05-31", autoload=False)

        assert len(trace_rows) == 1
        assert trace_rows[0]["source_table"] == "expenses"
        assert trace_rows[0]["source_type"] == "api_finance"
        assert trace_rows[0]["status"] == "PENDING"
        assert trace_rows[0]["confidence"] == "LOW"
        assert trace_rows[0]["traceable"] is True
        assert integrity["status"] == "PASS"
        assert any(item["category"] == "other" for item in integrity["accepted_warnings"])


if __name__ == "__main__":
    test_other_expenses_from_legacy_api_finance_are_traceable_but_not_confirmed()
    print("FINANCE OTHER SOURCE TRACEABILITY OK", flush=True)
