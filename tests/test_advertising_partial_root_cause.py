from __future__ import annotations

import importlib.util
import json
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
    db_path = str(tmp_path / "ads_audit.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    product_catalog.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_lookback_partial_but_report_period_complete_becomes_customer_ads_ok(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        meta = {
            "status": "ADS_PARTIAL",
            "period_begin": "2026-06-08",
            "period_end": "2026-07-07",
            "promotion_count_campaign_ids": [101, 999],
            "fullstats_requested_ids": [101, 999],
            "fullstats_returned_ids": [101],
            "missing_advert_ids": [999],
        }
        conn.execute(
            """
            INSERT INTO sync_state(
                telegram_id, sync_block, status, status_reason, rows_inserted, source_rows, updated_at, meta_json
            ) VALUES(658486226, 'advertising', 'PARTIAL', 'ADS_PARTIAL', 7, 1, '2026-07-07 12:00:00', ?)
            """,
            (json.dumps(meta, ensure_ascii=False),),
        )
        for day in range(1, 8):
            conn.execute(
                """
                INSERT INTO advertising(unique_key, telegram_id, advert_date, campaign_id, supplier_article, nm_id, spend, sum_price)
                VALUES(?, 658486226, ?, '101', 'SKU-1', 101, 100, 0)
                """,
                (f"adv-{day}", f"2026-07-0{day}"),
            )
        conn.commit()
    finally:
        conn.close()

    module = _load_module("audit_advertising_sync_test_ok", "scripts/audit_advertising_sync.py")
    audit = module.build_advertising_sync_audit(658486226, "2026-07-01", "2026-07-07")

    assert audit["raw_normalized_status"] == "ADS_PARTIAL"
    assert audit["campaigns_missing"] == 1
    assert audit["report_period_coverage_percent"] == 100.0
    assert audit["final_ads_status"] == "ADS_OK"
    assert audit["final_ads_reason"] == "report_period_complete_local_coverage_overrides_broad_lookback_partial"


def test_missing_campaign_without_local_rows_stays_partial(tmp_path):
    db_path = _prepare_db(tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        meta = {
            "status": "ADS_PARTIAL",
            "period_begin": "2026-07-01",
            "period_end": "2026-07-07",
            "promotion_count_campaign_ids": [101, 999],
            "fullstats_requested_ids": [101, 999],
            "fullstats_returned_ids": [101],
            "missing_advert_ids": [999],
        }
        conn.execute(
            """
            INSERT INTO sync_state(
                telegram_id, sync_block, status, status_reason, rows_inserted, source_rows, updated_at, meta_json
            ) VALUES(658486226, 'advertising', 'PARTIAL', 'ADS_PARTIAL', 2, 1, '2026-07-07 12:00:00', ?)
            """,
            (json.dumps(meta, ensure_ascii=False),),
        )
        conn.execute(
            """
            INSERT INTO advertising(unique_key, telegram_id, advert_date, campaign_id, supplier_article, nm_id, spend, sum_price)
            VALUES('adv-1', 658486226, '2026-07-01', '101', 'SKU-1', 101, 100, 0)
            """
        )
        conn.commit()
    finally:
        conn.close()

    module = _load_module("audit_advertising_sync_test_partial", "scripts/audit_advertising_sync.py")
    audit = module.build_advertising_sync_audit(658486226, "2026-07-01", "2026-07-07")

    assert audit["report_period_coverage_percent"] < 100.0
    assert audit["missing_campaigns_without_local_rows"] == ["999"]
    assert audit["final_ads_status"] == "ADS_PARTIAL"
    assert audit["final_ads_reason"] == "missing_campaigns_with_unknown_report_period_impact"
