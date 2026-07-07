from __future__ import annotations

import load_sales
from vooglii_finance.bridges import write_stock_snapshots_from_stocks


def sync_stocks(user_id: int, token: str, period: int | tuple[str, str]) -> dict:
    if isinstance(period, tuple):
        return {
            "raw_status": "WB_API_UNAVAILABLE_FOR_PERIOD",
            "source_name": "statistics-api.stocks",
            "source_rows": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "invalid": 0,
            "meta": {"note": "historical stocks unavailable; current snapshot only"},
        }
    loaded, status = load_sales.load_stocks(user_id, token)
    bridge = {"status": "SKIPPED", "rows": 0}
    if status == "SUCCESS":
        try:
            bridge = write_stock_snapshots_from_stocks(user_id)
        except Exception:
            bridge = {"status": "ERROR", "rows": 0}
    return {
        "raw_status": status,
        "source_name": "statistics-api.stocks",
        "source_rows": int(loaded or 0),
        "inserted": int(loaded or 0),
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "meta": {"loaded": int(loaded or 0), "stock_snapshots_bridge": bridge},
    }
