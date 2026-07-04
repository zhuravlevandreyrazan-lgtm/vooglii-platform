from __future__ import annotations

import sqlite3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
from db_manager import init_db
import telegram_bot


def test_advertising_health_snapshot_includes_campaign_linkability_metrics():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    telegram_id = 991002
    cur.execute("DELETE FROM advertising WHERE telegram_id=?", (telegram_id,))
    cur.execute("DELETE FROM expenses WHERE telegram_id=? AND expense_type='advertising'", (telegram_id,))
    cur.execute("DELETE FROM sync_status WHERE telegram_id=? AND sync_block='advertising'", (telegram_id,))
    cur.execute(
        """
        INSERT INTO advertising(
            unique_key, telegram_id, advert_date, campaign_id, campaign_name,
            supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "a1", telegram_id, "2026-07-01", "11", "Campaign 11",
            "SKU-1", 1001, "search", "SKU 1", 100, 20, 5, 5000.0, 300.0, 20.0, 15.0, 25.0,
        ),
    )
    cur.execute(
        """
        INSERT INTO advertising(
            unique_key, telegram_id, advert_date, campaign_id, campaign_name,
            supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "a2", telegram_id, "2026-07-01", "12", "Campaign 12",
            None, None, "search", "Unknown", 50, 10, 1, 1200.0, 100.0, 20.0, 10.0, 10.0,
        ),
    )
    cur.execute(
        """
        INSERT INTO expenses(unique_key, telegram_id, expense_date, expense_type, amount, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("exp-ads-1", telegram_id, "2026-07-01", "advertising", 400.0, "api_advertising", "2026-07-01 10:00:00"),
    )
    cur.execute(
        """
        INSERT INTO sync_status(telegram_id, sync_block, last_success, last_error, last_status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id, sync_block) DO UPDATE SET
            last_success=excluded.last_success,
            last_error=excluded.last_error,
            last_status=excluded.last_status,
            updated_at=excluded.updated_at
        """,
        (telegram_id, "advertising", "2026-07-01 10:00:00", None, "SUCCESS", "2026-07-01 10:00:00"),
    )
    conn.commit()
    conn.close()

    snapshot = telegram_bot.get_advertising_health_snapshot(telegram_id, "2026-07-01", "2026-07-01")

    assert snapshot["total_spend"] == 400.0
    assert snapshot["linked_spend"] == 300.0
    assert snapshot["unlinked_spend"] == 100.0
    assert snapshot["linkability_percent"] == 75.0
    assert snapshot["campaigns_total"] == 2
    assert snapshot["campaigns_linked"] == 1
    assert snapshot["campaigns_unlinked"] == 1
    assert snapshot["status"] == "MEDIUM"
