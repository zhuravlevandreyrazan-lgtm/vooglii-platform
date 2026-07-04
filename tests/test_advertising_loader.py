from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import load_sales


def test_load_ads_for_user_returns_normalized_partial_status(monkeypatch):
    monkeypatch.setattr(load_sales, "init_db", lambda: None)
    monkeypatch.setattr(load_sales, "WB_TOKEN", "token")
    monkeypatch.setattr(load_sales, "_acquire_local_sync_lock", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(load_sales, "_release_local_sync_lock", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(load_sales, "update_sync_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(load_sales, "save_update", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        load_sales,
        "_run_block",
        lambda *_args, **_kwargs: (3, "ADS_PARTIAL"),
    )
    monkeypatch.setattr(
        load_sales,
        "_get_last_ads_run_details",
        lambda _user_id: {"normalized_status": "ADS_PARTIAL", "missing_advert_ids": [111]},
    )

    loaded, status = load_sales.load_ads_for_user(telegram_id=42, wb_token="token", days=30)

    assert loaded == 3
    assert status["overall"] == "ERROR"
    assert status["blocks"]["advertising"]["status"] == "ADS_PARTIAL"
    assert status["blocks"]["advertising"]["details"]["normalized_status"] == "ADS_PARTIAL"


def test_normalize_advertising_status_maps_customer_safe_markers():
    assert load_sales.normalize_advertising_status("SUCCESS") == "ADS_OK"
    assert load_sales.normalize_advertising_status("ADS_PARTIAL_MISSING_IDS:1,2") == "ADS_PARTIAL"
    assert load_sales.normalize_advertising_status("ADS_PARTIAL") == "ADS_PARTIAL"
    assert load_sales.normalize_advertising_status("ADS_NO_CAMPAIGNS") == "ADS_NO_CAMPAIGNS"
    assert load_sales.normalize_advertising_status("RATE_LIMIT:60") == "ADS_API_LIMIT"
    assert load_sales.normalize_advertising_status("ERROR_401") == "ADS_AUTH_ERROR"
