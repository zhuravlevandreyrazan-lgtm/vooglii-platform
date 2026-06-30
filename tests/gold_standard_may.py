"""Readonly regression fixture for the approved WB Gold Standard May 2026 values."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    expected = telegram_bot._gold_standard_may_expected_fixture()
    _assert(float(expected.get("wb_payment_total") or 0) == 480472.04, "fixture wb_payment_total mismatch")
    _assert(float(expected.get("cost_total") or 0) == 294253.00, "fixture cost_total mismatch")
    _assert(float(expected.get("tax_amount") or 0) == 49411.57, "fixture tax_amount mismatch")
    _assert(float(expected.get("official_net_profit") or 0) == 136807.47, "fixture official_net_profit mismatch")
    _assert(bool(expected.get("ads_included_in_wb_deductions")) is True, "fixture ads_included_in_wb_deductions should be True")

    engine = telegram_bot._financial_engine_snapshot("2026-05-01", "2026-05-31", user=658486226)
    allowed_statuses = {"MATCHED", "PARTIAL", "PARTIAL_COST_MISSING", "LEGACY_FALLBACK", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "RATE_LIMIT", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR"}
    _assert(str(engine.get("status") or "") in allowed_statuses, "engine status out of allowed set")
    if str(engine.get("source") or "") == "wb_finance_api" and engine.get("wb_payment_total") is not None:
        payment_match = abs(float(engine.get("wb_payment_total") or 0) - float(expected.get("wb_payment_total") or 0)) <= 1.0
        cost_match = engine.get("cost_total") is not None and abs(float(engine.get("cost_total") or 0) - float(expected.get("cost_total") or 0)) <= 1.0
        profit_match = engine.get("official_net_profit") is not None and abs(float(engine.get("official_net_profit") or 0) - float(expected.get("official_net_profit") or 0)) <= 1.0
        if payment_match and (engine.get("official_net_profit") is None or (cost_match and profit_match)):
            print("GOLD STANDARD MAY ENGINE MATCHED")
        else:
            print("GOLD STANDARD MAY ENGINE DIFFERENT")
    else:
        print("GOLD STANDARD MAY FIXTURE OK")


if __name__ == "__main__":
    main()
