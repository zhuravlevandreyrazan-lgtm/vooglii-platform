from __future__ import annotations

from product_catalog import sync_product_catalog


def refresh_products_index(user_id: int, period: int | tuple[str, str] | None = None) -> dict[str, int | str | dict]:
    result = sync_product_catalog(int(user_id), period=period)
    return {
        "inserted": int(result.get("inserted") or 0),
        "updated": int(result.get("updated") or 0),
        "skipped": int(result.get("skipped") or 0),
        "invalid": int(result.get("invalid") or 0),
        "source_rows": int(result.get("source_rows") or 0),
        "raw_status": str(result.get("status") or "OK"),
        "meta": dict(result.get("meta") or {}),
    }
