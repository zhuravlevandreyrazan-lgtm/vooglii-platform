from __future__ import annotations

import sqlite3

from config import DB_NAME
from db_manager import init_db


def refresh_products_index(user_id: int) -> dict[str, int]:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        before = conn.total_changes
        cur.execute(
            """
            INSERT OR IGNORE INTO products (telegram_id, supplier_article, cost_price, last_price)
            SELECT ?, supplier_article, 0, MAX(price_with_disc)
            FROM sales
            WHERE telegram_id=? AND supplier_article IS NOT NULL
            GROUP BY supplier_article
            """,
            (int(user_id), int(user_id)),
        )
        conn.commit()
        inserted = max(0, int(conn.total_changes - before))
        return {"inserted": inserted, "updated": 0, "skipped": 0, "source_rows": inserted}
    finally:
        conn.close()
