from __future__ import annotations

from typing import Any


def infer_root_cause(metric: str, wb_value: Any, vooglii_value: Any, snapshot: dict[str, Any]) -> str:
    if wb_value is None:
        return "wb_report_field_missing"
    if vooglii_value is None:
        if metric in {"revenue", "payout", "logistics", "storage", "acquiring", "wb_deductions", "other_expenses"}:
            return "field_unavailable"
        if metric in {"orders_count", "buyouts_count", "returns_count"}:
            return "missing_sales_rows"
        return "field_unavailable"
    source_map = dict(snapshot.get("source_map") or {})
    if metric in {"orders_count", "buyouts_count", "returns_count"} and vooglii_value in (None, 0):
        return "missing_sales_rows"
    if metric == "advertising" and vooglii_value in (None, 0):
        return "wrong_reason_mapping"
    if metric in {"logistics", "storage", "acquiring", "wb_deductions", "other_expenses", "penalties"}:
        finance_raw_rows = int((snapshot.get("source_rows") or {}).get("finance_raw_audit") or 0)
        if finance_raw_rows <= 0:
            return "missing_finance_raw_rows"
    source_entry = {}
    field_mapping = {
        "revenue": "wb_sale_amount",
        "payout": "wb_payout_amount",
        "logistics": "wb_logistics",
        "storage": "wb_storage",
        "acquiring": "wb_acquiring",
        "wb_deductions": "wb_deductions",
        "other_expenses": "wb_other",
        "penalties": "penalties",
        "advertising": "advertising",
    }
    mapped_field = field_mapping.get(metric)
    if mapped_field:
        source_entry = dict(source_map.get(mapped_field) or {})
        candidates = list(source_entry.get("candidates") or [])
        if source_entry.get("selected_source") is None and not candidates:
            return "field_unavailable"
    delta = abs(float(vooglii_value) - float(wb_value))
    if 0 < delta < 1:
        return "rounding_difference"
    if metric == "payout":
        total_to_pay = snapshot.get("wb_total_to_pay")
        if total_to_pay not in (None, 0) and abs(float(total_to_pay) - float(wb_value)) < delta:
            return "period_mismatch"
    if metric == "revenue":
        return "model_mismatch_management_vs_wb_weekly"
    return "unknown"
