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
    import telegram_bot
    import vooglii_finance.unified_snapshot as unified_snapshot

    importlib.reload(config)
    importlib.reload(db_manager)
    importlib.reload(telegram_bot)
    importlib.reload(unified_snapshot)
    return config, db_manager, telegram_bot, unified_snapshot


def test_snapshot_build_writes_financial_snapshot_audit(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, db_manager, telegram_bot, unified_snapshot = _reload_modules(tmp_dir)
        db_manager.init_db()

        monkeypatch.setattr(telegram_bot, "_center_days", lambda days: days)
        monkeypatch.setattr(telegram_bot, "_period_dates", lambda days: days)
        monkeypatch.setattr(telegram_bot, "_report_mgmt_snapshot", lambda *_args, **_kwargs: {"revenue": 1000.0, "payout": 700.0, "cost_price": 300.0, "advertising": 100.0, "logistics": 50.0, "storage": 10.0, "other": 5.0, "acquiring": 2.0, "deductions": 3.0, "unexplained": 0.0})
        monkeypatch.setattr(telegram_bot, "_advertising_customer_snapshot", lambda *_args, **_kwargs: {"normalized_status": "ADS_OK", "status_kind": "ready", "total_spend": 100.0})
        monkeypatch.setattr(telegram_bot, "_products_center_snapshot", lambda *_args, **_kwargs: {"cost_coverage_percent": 100.0})
        monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda *_args, **_kwargs: {"status": "OK"})
        monkeypatch.setattr(telegram_bot, "_financial_engine_snapshot", lambda *_args, **_kwargs: {"official_new_finance_available": True, "official_net_profit": 530.0, "cost_total": 300.0, "tax_amount": 0.0})
        monkeypatch.setattr(telegram_bot, "_payment_reconciliation_snapshot", lambda *_args, **_kwargs: {"weekly_payout_total_all": 700.0, "sales_for_pay_total": 700.0, "sales_revenue_total": 1000.0})
        monkeypatch.setattr(telegram_bot, "get_finance_difference_snapshot", lambda *_args, **_kwargs: {"coverage_percent": 100.0, "logistics": 50.0, "storage": 10.0, "acquiring": 2.0, "deductions": 3.0, "explicit_other_deductions": 5.0, "other_deductions": 5.0, "residual_other_deductions": 0.0})
        monkeypatch.setattr(telegram_bot, "_data_quality_snapshot", lambda *_args, **_kwargs: {"overall_status": "HIGH", "sales": {"status": "OK"}})
        monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda *_args, **_kwargs: (10, 1000.0, 0, 0.0))
        monkeypatch.setattr(telegram_bot, "get_period_stats", lambda *_args, **_kwargs: (9, 1000.0))
        monkeypatch.setattr(telegram_bot, "get_profit_stats", lambda *_args, **_kwargs: (1000.0, 0.0, 700.0, 300.0, 50.0, 100.0, 10.0, 5.0, 470.0, 0.0, 530.0, 53.0, 1))
        monkeypatch.setattr(telegram_bot, "get_profit_stats_after_tax", lambda *_args, **_kwargs: {"profit_before_tax": 530.0, "tax": 0.0, "profit_after_tax": 530.0, "tax_configured": False})

        payload = unified_snapshot.build_unified_financial_snapshot_dict(42, ("2026-05-01", "2026-05-31"), bot=telegram_bot)

        conn = sqlite3.connect(config.DB_NAME)
        row = conn.execute("SELECT revenue, expenses_total, net_profit, source_map_json FROM financial_snapshot_audit WHERE user_id=42").fetchone()
        conn.close()

        assert payload["snapshot_audit"]["status"] == "OK"
        assert row is not None
        assert round(float(row[0] or 0), 2) == 1000.0
        assert round(float(row[2] or 0), 2) == 530.0
        assert "sales_revenue" in str(row[3] or "")


if __name__ == "__main__":
    test_snapshot_build_writes_financial_snapshot_audit(__import__("pytest").MonkeyPatch())
    print("FINANCIAL SNAPSHOT AUDIT OK", flush=True)
