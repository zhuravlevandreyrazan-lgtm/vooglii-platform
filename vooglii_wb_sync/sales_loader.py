from __future__ import annotations

import load_sales


def sync_sales(user_id: int, token: str, period: int | tuple[str, str]) -> dict:
    if isinstance(period, tuple):
        result = load_sales.backfill_sales_orders_range(user_id, token, period[0], period[1])
        stats = result.get("sales_db") or {}
        return {
            "raw_status": (result.get("sales_api") or {}).get("status") or result.get("status"),
            "source_name": "statistics-api.sales",
            "source_rows": int((result.get("sales_api") or {}).get("rows_in_range") or 0),
            "inserted": int(stats.get("inserted") or 0),
            "updated": int(stats.get("updated") or 0),
            "skipped": int(stats.get("skipped") or 0),
            "invalid": int(stats.get("invalid") or 0),
            "meta": result,
        }
    loaded, status = load_sales.load_sales(user_id, token, period)
    return {
        "raw_status": status,
        "source_name": "statistics-api.sales",
        "source_rows": int(loaded or 0),
        "inserted": int(loaded or 0),
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "meta": {"loaded": int(loaded or 0)},
    }
