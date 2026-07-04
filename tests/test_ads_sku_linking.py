from __future__ import annotations

import sqlite3
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
from db_manager import init_db
from load_sales import _replace_advert_sku_links


def test_replace_advert_sku_links_writes_customer_link_rows():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM advert_sku_links WHERE telegram_id=?", (991001,))
    rows = [
        (
            "ad:991001:2026-07-01:11:search:1001:SKU-1",
            991001,
            "2026-07-01",
            "11",
            "Campaign 11",
            "SKU-1",
            1001,
            "search",
            "SKU 1",
            10,
            5,
            2,
            1500.0,
            300.0,
            50.0,
            60.0,
            40.0,
        ),
        (
            "ad:991001:2026-07-01:12:search:None:None",
            991001,
            "2026-07-01",
            "12",
            "Campaign 12",
            None,
            None,
            "search",
            "SKU unknown",
            8,
            4,
            1,
            800.0,
            120.0,
            50.0,
            30.0,
            25.0,
        ),
    ]

    written = _replace_advert_sku_links(cur, 991001, rows)
    conn.commit()
    cur.execute(
        """
        SELECT advert_id, campaign_name, nm_id, supplier_article, source, confidence
        FROM advert_sku_links
        WHERE telegram_id=?
        ORDER BY advert_id
        """,
        (991001,),
    )
    saved = cur.fetchall()
    conn.close()

    assert written == 2
    assert saved[0] == ("11", "Campaign 11", 1001, "SKU-1", "fullstats_direct", "high")
    assert saved[1] == ("12", "Campaign 12", None, None, "unlinked", "low")
