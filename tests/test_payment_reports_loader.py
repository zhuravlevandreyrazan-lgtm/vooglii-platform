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


def test_sync_payment_reports_sums_retail_amount_sum_for_2026_06_22_week():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, legacy_bot, finance_loader, sync_state = _reload_modules(tmp_dir)
        legacy_bot.fetch_wb_finance_reports_list = lambda *_args, **_kwargs: {
            "status": "SUCCESS",
            "rows": [
                legacy_bot._normalize_finance_report_row(
                    {
                        "reportId": "report-1",
                        "dateFrom": "2026-06-22",
                        "dateTo": "2026-06-28",
                        "createDate": "2026-06-29T10:00:00",
                        "reportType": "1",
                        "retailAmountSum": 7846.00,
                        "forPaySum": 7600.00,
                        "bankPaymentSum": 4300.00,
                        "deliveryServiceSum": 1800.00,
                        "paidStorageSum": 200.00,
                        "deductionSum": 900.00,
                    }
                ),
                legacy_bot._normalize_finance_report_row(
                    {
                        "reportId": "report-2",
                        "dateFrom": "2026-06-22",
                        "dateTo": "2026-06-28",
                        "createDate": "2026-06-29T10:01:00",
                        "reportType": "2",
                        "retailAmountSum": 549.94,
                        "forPaySum": 500.00,
                        "bankPaymentSum": 300.00,
                        "deliveryServiceSum": 100.00,
                        "paidStorageSum": 20.00,
                        "deductionSum": 30.00,
                    }
                ),
            ],
            "message": "ok",
        }

        result = finance_loader.sync_payment_reports(42, "token", ("2026-06-22", "2026-06-28"))
        assert result["raw_status"] == "SUCCESS"

        sync_state.save_sync_state(
            42,
            "payment_reports",
            "OK",
            status_reason="SUCCESS",
            source_rows=2,
            source_name="finance-api.sales-reports-list",
        )
        legacy_bot._invalidate_payment_reports_source_cache(42, "2026-06-22", "2026-06-28")
        payload = legacy_bot._payment_reports_source_data(42, "2026-06-22", "2026-06-28")

        assert payload["source"] == "wb_api"
        assert len(payload["rows"]) == 2
        assert round(sum(float(item.get("revenue") or 0) for item in payload["rows"]), 2) == 8395.94

        conn = sqlite3.connect(config.DB_NAME)
        try:
            revenue = conn.execute(
                "SELECT ROUND(COALESCE(SUM(revenue),0), 2) FROM payment_reports_rows WHERE user_id=42 AND date_from='2026-06-22' AND date_to='2026-06-28'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert revenue == 8395.94


def test_persist_payment_report_rows_twice_updates_without_integrity_error():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config, _legacy_bot, finance_loader, _sync_state = _reload_modules(tmp_dir)
        first = [
            {
                "report_id": "same-report",
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
                "raw_json": '{"reportId":"same-report","forPaySum":15327.09}',
            }
        ]
        second = [
            {
                "report_id": "same-report",
                "period_start": "2026-06-29",
                "period_end": "2026-07-05",
                "create_date": "2026-07-07T12:00:00",
                "type": "main",
                "revenue": 15000.00,
                "for_pay": 16000.00,
                "bank_payment": 9100.00,
                "delivery": 3400.00,
                "storage": 640.00,
                "deduction": 2200.00,
                "penalty": 10.0,
                "additional_payment": 5.0,
                "payment_schedule": "weekly-updated",
                "currency_name": "RUB",
                "source_type": "wb_api",
                "raw_json": '{"reportId":"same-report","forPaySum":16000.00}',
            }
        ]

        first_result = finance_loader._persist_payment_report_rows(42, first, "2026-06-29", "2026-07-05")
        second_result = finance_loader._persist_payment_report_rows(42, second, "2026-06-29", "2026-07-05")

        assert first_result["inserted"] == 1
        assert second_result["updated"] == 1
        conn = sqlite3.connect(config.DB_NAME)
        try:
            row = conn.execute(
                "SELECT create_date, revenue, for_pay, bank_payment, delivery, storage, deduction, penalty, additional_payment, payment_schedule, currency_name, source_type, raw_json, created_at "
                "FROM payment_reports_rows WHERE user_id=42 AND report_id='same-report' AND report_type='main' AND date_from='2026-06-29' AND date_to='2026-07-05'"
            ).fetchone()
        finally:
            conn.close()

        assert row[:13] == (
            "2026-07-06T10:00:00",
            15000.0,
            16000.0,
            9100.0,
            3400.0,
            640.0,
            2200.0,
            10.0,
            5.0,
            "weekly-updated",
            "RUB",
            "wb_api",
            '{"reportId":"same-report","forPaySum":16000.00}',
        )
        assert row[13] is not None


if __name__ == "__main__":
    test_sync_payment_reports_persists_rows_and_reads_from_db()
    test_sync_payment_reports_no_rows_status()
    test_sync_payment_reports_persists_revenue_from_real_alternative_wb_field()
    test_sync_payment_reports_sums_retail_amount_sum_for_2026_06_22_week()
    test_persist_payment_report_rows_twice_updates_without_integrity_error()
    print("PAYMENT REPORTS LOADER OK", flush=True)
