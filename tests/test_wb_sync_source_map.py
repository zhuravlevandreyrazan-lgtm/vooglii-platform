from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import vooglii_wb_sync.advertising_loader as advertising_loader


def test_advertising_loader_exposes_selected_source(monkeypatch):
    monkeypatch.setattr(advertising_loader.load_sales, "backfill_advertising_period", lambda *_args, **_kwargs: (5, "ADS_PARTIAL"))
    monkeypatch.setattr(
        advertising_loader.load_sales,
        "_get_last_ads_run_details",
        lambda _user_id: {"campaigns_found": 7, "campaigns_sent": 5, "missing_advert_ids": [1001], "advert_ids_received": 4},
    )

    payload = advertising_loader.sync_advertising(1, "token", ("2026-06-01", "2026-06-30"))

    assert payload["raw_status"] == "ADS_PARTIAL"
    assert payload["source_map"]["selected_source"] == "advertising"
    assert payload["source_map"]["missing_advert_ids"] == [1001]


if __name__ == "__main__":
    test_advertising_loader_exposes_selected_source(__import__("pytest").MonkeyPatch())
    print("WB SYNC SOURCE MAP OK", flush=True)
