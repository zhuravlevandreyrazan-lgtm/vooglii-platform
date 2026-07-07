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


def test_finance_source_integrity_report_passes_when_layers_match():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, db_manager, bridges = _reload_modules(tmp_dir)
        db_manager.init_db()
        conn = sqlite3.connect(config.DB_NAME)
        conn.execute("INSERT INTO expenses(unique_key, telegram_id, expense_date, expense_type, amount, source) VALUES('exp-1', 42, '2026-05-11', 'logistics', 35.0, 'api_finance')")
        conn.execute("INSERT INTO finance_raw_audit(telegram_id, rrd_id, report_date, deduction, acquiring_fee, penalty, acceptance, acceptance_fee, additional_payment, created_at) VALUES(42, 'rrd-1', '2026-05-11', 7.0, 3.0, 2.0, 1.0, 0.5, 0.5, '2026-05-11 10:00:00')")
        conn.commit()
        conn.close()

        report = bridges.build_finance_source_integrity_report(42, "2026-05-01", "2026-05-31")

        assert report["status"] == "PASS"
        assert report["mismatches"] == []
        assert report["finance_raw_to_events"]["wb_deductions"]["finance_raw_audit"] == 7.0
        assert report["finance_raw_to_events"]["wb_deductions"]["finance_expense_events"] == 7.0
        assert report["categories"]["other"]["amount"] == 2.0


if __name__ == "__main__":
    test_finance_source_integrity_report_passes_when_layers_match()
    print("FINANCE SOURCE INTEGRITY OK", flush=True)
