from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_modules(tmp_dir: str):
    os.environ["DB_DIR"] = tmp_dir
    os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"
    import config
    import db_manager
    import vooglii_telegram.legacy_bot as legacy_bot
    import vooglii_wb_sync.finance_loader as finance_loader
    import vooglii_wb_sync.sync_state as sync_state

    importlib.reload(config)
    importlib.reload(db_manager)
    importlib.reload(legacy_bot)
    importlib.reload(finance_loader)
    importlib.reload(sync_state)
    legacy_bot.DB_NAME = config.DB_NAME
    finance_loader.DB_NAME = config.DB_NAME
    db_manager.init_db()
    return config, legacy_bot, finance_loader, sync_state


def _fixture_rows():
    return [
        {
            "report_id": "main-2026-06-29",
            "period_start": "2026-06-29",
            "period_end": "2026-07-05",
            "create_date": "2026-07-06T10:00:00",
            "type": "main",
            "revenue": 14046.08,
            "for_pay": 15327.09,
            "bank_payment": 9084.94,
            "delivery": 3463.06,
            "storage": 631.09,
            "deduction": 2148.00,
            "penalty": 0.0,
            "additional_payment": 0.0,
            "payment_schedule": "weekly",
            "currency_name": "RUB",
            "raw_json": '{"reportId":"main-2026-06-29","reportType":"main","bankPaymentSum":9084.94}',
        },
        {
            "report_id": "buyout-2026-06-29",
            "period_start": "2026-06-29",
            "period_end": "2026-07-05",
            "create_date": "2026-07-06T10:01:00",
            "type": "buyout",
            "revenue": 0.0,
            "for_pay": 0.0,
            "bank_payment": 0.0,
            "delivery": 0.0,
            "storage": 0.0,
            "deduction": 0.0,
            "penalty": 0.0,
            "additional_payment": 0.0,
            "payment_schedule": "weekly",
            "currency_name": "RUB",
            "raw_json": '{"reportId":"buyout-2026-06-29","reportType":"buyout","bankPaymentSum":0}',
        },
    ]


def test_sync_payment_reports_persists_rows_and_reads_from_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, legacy_bot, finance_loader, sync_state = _reload_modules(tmp_dir)

        legacy_bot.fetch_wb_finance_reports_list = lambda *_args, **_kwargs: {
            "status": "SUCCESS",
            "rows": _fixture_rows(),
            "message": "ok",
        }

        first = finance_loader.sync_payment_reports(42, "token", ("2026-06-29", "2026-07-05"))
        second = finance_loader.sync_payment_reports(42, "token", ("2026-06-29", "2026-07-05"))

        assert first["raw_status"] == "SUCCESS"
        assert first["inserted"] == 2
        assert first["updated"] == 0
        assert second["inserted"] == 0
        assert second["updated"] == 0
        assert second["skipped"] == 2

        conn = sqlite3.connect(config.DB_NAME)
        try:
            count = conn.execute("SELECT COUNT(*) FROM payment_reports_rows WHERE user_id=42").fetchone()[0]
            main_row = conn.execute(
                "SELECT report_id, revenue, for_pay, bank_payment, delivery, storage, deduction, source_type "
                "FROM payment_reports_rows WHERE user_id=42 AND report_type='main'"
            ).fetchone()
        finally:
            conn.close()

        assert count == 2
        assert main_row == ("main-2026-06-29", 14046.08, 15327.09, 9084.94, 3463.06, 631.09, 2148.0, "wb_api")

        sync_state.save_sync_state(
            42,
            "payment_reports",
            "OK",
            status_reason="SUCCESS",
            source_rows=2,
            source_name="finance-api.sales-reports-list",
        )
        legacy_bot._invalidate_payment_reports_source_cache(42, "2026-06-29", "2026-07-05")
        payload = legacy_bot._payment_reports_source_data(42, "2026-06-29", "2026-07-05")

        assert payload["source"] == "wb_api"
        assert payload["status"] == "OK"
        assert len(payload["rows"]) == 2


def test_sync_payment_reports_no_rows_status():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, legacy_bot, finance_loader, _sync_state = _reload_modules(tmp_dir)
        conn = sqlite3.connect(config.DB_NAME)
        try:
            conn.execute(
                "INSERT INTO payment_reports_rows(user_id, report_id, date_from, date_to, report_type, source_type, created_at, updated_at) "
                "VALUES(42, 'stale', '2026-06-29', '2026-07-05', 'main', 'wb_api', '2026-07-09 10:00:00', '2026-07-09 10:00:00')"
            )
            conn.commit()
        finally:
            conn.close()
        legacy_bot.fetch_wb_finance_reports_list = lambda *_args, **_kwargs: {
            "status": "EMPTY",
            "rows": [],
            "message": "No finance reports returned",
        }

        result = finance_loader.sync_payment_reports(42, "token", ("2026-06-29", "2026-07-05"))

        assert result["raw_status"] == "NO_ROWS"
        assert result["source_rows"] == 0
        conn = sqlite3.connect(config.DB_NAME)
        try:
            count = conn.execute("SELECT COUNT(*) FROM payment_reports_rows WHERE user_id=42").fetchone()[0]
        finally:
            conn.close()
        assert count == 0


def test_sync_payment_reports_persists_revenue_from_real_alternative_wb_field():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, legacy_bot, finance_loader, _sync_state = _reload_modules(tmp_dir)
        legacy_bot.fetch_wb_finance_reports_list = lambda *_args, **_kwargs: {
            "status": "SUCCESS",
            "rows": [
                {
                    "report_id": "main-2026-06-29",
                    "period_start": "2026-06-29",
                    "period_end": "2026-07-05",
                    "create_date": "2026-07-06T10:00:00",
                    "type": "main",
                    "revenue": 14046.08,
                    "for_pay": 15327.09,
                    "bank_payment": 9084.94,
                    "delivery": 3463.06,
                    "storage": 631.09,
                    "deduction": 2148.00,
                    "penalty": 0.0,
                    "additional_payment": 0.0,
                    "payment_schedule": "weekly",
                    "currency_name": "RUB",
                    "raw_json": '{"saleSum":14046.08,"forPaySum":15327.09,"bankPaymentSum":9084.94,"deliveryServiceSum":3463.06,"paidStorageSum":631.09,"deductionSum":2148.00}',
                }
            ],
            "message": "ok",
        }

        result = finance_loader.sync_payment_reports(42, "token", ("2026-06-29", "2026-07-05"))

        assert result["raw_status"] == "SUCCESS"
        conn = sqlite3.connect(config.DB_NAME)
        try:
            revenue = conn.execute(
                "SELECT revenue FROM payment_reports_rows WHERE user_id=42 AND report_id='main-2026-06-29'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert revenue == 14046.08


if __name__ == "__main__":
    test_sync_payment_reports_persists_rows_and_reads_from_db()
    test_sync_payment_reports_no_rows_status()
    test_sync_payment_reports_persists_revenue_from_real_alternative_wb_field()
    print("PAYMENT REPORTS LOADER OK", flush=True)
