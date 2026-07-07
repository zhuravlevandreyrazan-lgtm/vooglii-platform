from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_wb_sync import rate_limiter


def test_parse_status_kind_maps_expected_statuses():
    assert rate_limiter.parse_status_kind("SUCCESS") == "OK"
    assert rate_limiter.parse_status_kind("NO_TOKEN") == "NO_TOKEN"
    assert rate_limiter.parse_status_kind("RATE_LIMIT:60") == "API_LIMIT"
    assert rate_limiter.parse_status_kind("ADS_PARTIAL") == "PARTIAL"
    assert rate_limiter.parse_status_kind("WB_API_UNAVAILABLE_FOR_PERIOD") == "UNAVAILABLE"
    assert rate_limiter.parse_status_kind("EXCEPTION:Timeout") == "ERROR"


if __name__ == "__main__":
    test_parse_status_kind_maps_expected_statuses()
    print("WB SYNC RATE LIMITER OK", flush=True)
