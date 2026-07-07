from __future__ import annotations

import load_sales


def sync_advertising(user_id: int, token: str, period: int | tuple[str, str]) -> dict:
    if isinstance(period, tuple):
        loaded, status = load_sales.backfill_advertising_period(
            user_id,
            token,
            period[0],
            period[1],
            token_source="vooglii_wb_sync.advertising_loader",
        )
    else:
        loaded, status = load_sales.load_advertising(
            user_id,
            token,
            period,
            token_source="vooglii_wb_sync.advertising_loader",
        )
    details = load_sales._get_last_ads_run_details(user_id) or {}
    return {
        "raw_status": status,
        "source_name": "advert-api.fullstats",
        "source_rows": int(details.get("advert_ids_received") or loaded or 0),
        "inserted": int(loaded or 0),
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "meta": details,
        "source_map": {
            "campaigns_found": int(details.get("campaigns_found") or 0),
            "campaigns_sent": int(details.get("campaigns_sent") or 0),
            "missing_advert_ids": list(details.get("missing_advert_ids") or []),
            "selected_source": "advertising",
        },
    }
