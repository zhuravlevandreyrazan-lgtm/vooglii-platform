from __future__ import annotations

from typing import Any


def infer_root_cause(metric: str, wb_value: Any, vooglii_value: Any, snapshot: dict[str, Any]) -> str:
    if wb_value is None:
        return "wb_report_field_missing"
    if metric == "advertising":
        source = dict((snapshot.get("source_map") or {}).get("advertising_spend") or {})
        drift = float(source.get("drift_amount") or 0)
        if 0 < drift < 1:
            return "rounding_difference"
        if float(snapshot.get("advertising_spend") or 0) <= 0:
            return "missing_advertising_rows"
    if metric in {"revenue", "orders_count", "buyouts_count", "returns_count"} and vooglii_value in (None, 0):
        return "missing_sales_rows"
    if metric in {"logistics", "storage", "acquiring", "wb_deductions", "other_expenses", "penalties", "payout"}:
        if str(snapshot.get("finance_confidence") or "").upper() not in {"HIGH", "MEDIUM"}:
            return "partial_finance_confidence"
        if vooglii_value in (None, 0):
            return "missing_finance_rows"
    if metric == "cost_price" and vooglii_value in (None, 0):
        return "cost_missing"
    if not snapshot.get("source_map"):
        return "source_map_missing"
    if str(snapshot.get("ads_status") or "").upper() == "ADS_API_LIMIT":
        return "api_limit"
    return "unknown"
