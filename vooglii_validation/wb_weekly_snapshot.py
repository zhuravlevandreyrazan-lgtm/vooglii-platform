from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date
from typing import Any

import config
from db_manager import init_db

from .models import WBWeeklySnapshot


RAW_LOGISTICS_KEYS = (
    "delivery_rub",
    "rebill_logistic_cost",
    "return_amount",
    "delivery_amount",
)
RAW_STORAGE_KEYS = ("storage_fee", "storage", "storage_cost")
RAW_REVENUE_KEYS = ("retail_amount", "retail_price_withdisc_rub", "sale_amount", "ppvz_sales_commission")
RAW_PAYOUT_KEYS = ("ppvz_for_pay", "supplier_operating_reward", "supplier_payment", "to_pay", "payment_amount")
RAW_TOTAL_TO_PAY_KEYS = ("ppvz_for_pay", "to_pay", "payment_amount")


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _sum_row_keys(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    values = []
    for key in keys:
        amount = _money(payload.get(key))
        if amount is not None:
            values.append(abs(amount))
    if not values:
        return None
    return round(sum(values), 2)


def _sum_values(values: list[float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    if not known:
        return None
    return round(sum(known), 2)


def _pick_source(candidates: list[tuple[str, float | None, int]]) -> tuple[str | None, float | None, int]:
    fallback: tuple[str | None, float | None, int] = (None, None, 0)
    for source_name, value, rows in candidates:
        if value is None:
            continue
        return source_name, _money(value), int(rows or 0)
    return fallback


def _fetch_sales_counts(conn: sqlite3.Connection, user_id: int, period_from: date, period_to: date) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN COALESCE(is_return, 0)=0 THEN 1 ELSE 0 END), 0) AS sales_count,
            COALESCE(SUM(CASE WHEN COALESCE(is_return, 0)=1 THEN 1 ELSE 0 END), 0) AS returns_count
        FROM sales
        WHERE telegram_id=? AND substr(sale_date, 1, 10) BETWEEN ? AND ?
        """,
        (int(user_id), str(period_from), str(period_to)),
    ).fetchone()
    orders_row = conn.execute(
        """
        SELECT COUNT(*)
        FROM orders
        WHERE telegram_id=? AND substr(order_date, 1, 10) BETWEEN ? AND ?
        """,
        (int(user_id), str(period_from), str(period_to)),
    ).fetchone()
    sales_count = int(row["sales_count"] or 0) if row else 0
    returns_count = int(row["returns_count"] or 0) if row else 0
    return {
        "sales_count": sales_count,
        "returns_count": returns_count,
        "orders_count": int(orders_row[0] or 0) if orders_row else 0,
    }


def _fetch_grouped_events(
    conn: sqlite3.Connection,
    user_id: int,
    period_from: date,
    period_to: date,
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT expense_category, COALESCE(SUM(amount), 0) AS total_amount, COUNT(*) AS rows_count
        FROM finance_expense_events
        WHERE user_id=? AND substr(event_date, 1, 10) BETWEEN ? AND ?
        GROUP BY expense_category
        """,
        (int(user_id), str(period_from), str(period_to)),
    ).fetchall()
    return {
        str(row["expense_category"]): {
            "amount": _money(row["total_amount"]),
            "rows": int(row["rows_count"] or 0),
        }
        for row in rows
    }


def _fetch_grouped_expenses(
    conn: sqlite3.Connection,
    user_id: int,
    period_from: date,
    period_to: date,
) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT expense_type, COALESCE(SUM(amount), 0) AS total_amount, COUNT(*) AS rows_count
        FROM expenses
        WHERE telegram_id=? AND substr(expense_date, 1, 10) BETWEEN ? AND ?
        GROUP BY expense_type
        """,
        (int(user_id), str(period_from), str(period_to)),
    ).fetchall()
    return {
        str(row["expense_type"]): {
            "amount": _money(row["total_amount"]),
            "rows": int(row["rows_count"] or 0),
        }
        for row in rows
    }


def _fetch_payment_snapshot(user_id: int, period_from: date, period_to: date) -> dict[str, Any]:
    try:
        from vooglii_finance.unified_snapshot import _get_bot  # type: ignore

        bot = _get_bot()
        snapshot = bot._payment_reconciliation_snapshot(int(user_id), str(period_from), str(period_to))
        return dict(snapshot or {})
    except Exception:
        return {}


def _build_raw_summary(
    conn: sqlite3.Connection,
    user_id: int,
    period_from: date,
    period_to: date,
) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT *
        FROM finance_raw_audit
        WHERE telegram_id=? AND substr(report_date, 1, 10) BETWEEN ? AND ?
        ORDER BY report_date ASC, id ASC
        """,
        (int(user_id), str(period_from), str(period_to)),
    ).fetchall()
    raw_logistics_values: list[float | None] = []
    raw_storage_values: list[float | None] = []
    raw_revenue_values: list[float | None] = []
    raw_payout_values: list[float | None] = []
    raw_total_to_pay_values: list[float | None] = []
    operation_types: dict[str, int] = {}
    for row in rows:
        payload = {}
        try:
            payload = json.loads(str(row["raw_json"] or "") or "{}")
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            raw_logistics_values.append(_sum_row_keys(payload, RAW_LOGISTICS_KEYS))
            raw_storage_values.append(_sum_row_keys(payload, RAW_STORAGE_KEYS))
            raw_revenue_values.append(_sum_row_keys(payload, RAW_REVENUE_KEYS))
            raw_payout_values.append(_sum_row_keys(payload, RAW_PAYOUT_KEYS))
            raw_total_to_pay_values.append(_sum_row_keys(payload, RAW_TOTAL_TO_PAY_KEYS))
        operation_name = str(row["operation_type"] or row["doc_type_name"] or "").strip()
        if operation_name:
            operation_types[operation_name] = int(operation_types.get(operation_name, 0)) + 1
    penalties = _sum_values([abs(_money(row["penalty"]) or 0.0) for row in rows]) if rows else None
    summary = {
        "rows": int(len(rows)),
        "logistics": _sum_values(raw_logistics_values),
        "storage": _sum_values(raw_storage_values),
        "revenue": _sum_values(raw_revenue_values),
        "payout": _sum_values(raw_payout_values),
        "total_to_pay": _sum_values(raw_total_to_pay_values),
        "acquiring": _sum_values([abs(_money(row["acquiring_fee"]) or 0.0) for row in rows]) if rows else None,
        "wb_deductions": _sum_values([abs(_money(row["deduction"]) or 0.0) for row in rows]) if rows else None,
        "other": _sum_values(
            [
                abs(_money(row["penalty"]) or 0.0)
                + abs(_money(row["acceptance"]) or 0.0)
                + abs(_money(row["acceptance_fee"]) or 0.0)
                + abs(_money(row["additional_payment"]) or 0.0)
                for row in rows
            ]
        )
        if rows
        else None,
        "penalties": penalties,
        "operation_types": operation_types,
    }
    return summary


def _source_entry(selected_source: str | None, selected_value: float | int | None, rows: int, candidates: list[tuple[str, Any, int]]) -> dict[str, Any]:
    return {
        "selected_source": selected_source,
        "selected_value": selected_value,
        "rows": int(rows or 0),
        "candidates": [
            {
                "source": source_name,
                "value": _money(value) if isinstance(value, (int, float)) or value is None else value,
                "rows": int(source_rows or 0),
            }
            for source_name, value, source_rows in candidates
        ],
    }


def build_wb_weekly_snapshot(user_id: int, period_from: date, period_to: date) -> WBWeeklySnapshot:
    conn = _connect()
    try:
        counts = _fetch_sales_counts(conn, int(user_id), period_from, period_to)
        raw = _build_raw_summary(conn, int(user_id), period_from, period_to)
        events = _fetch_grouped_events(conn, int(user_id), period_from, period_to)
        expenses = _fetch_grouped_expenses(conn, int(user_id), period_from, period_to)
        payment_snapshot = _fetch_payment_snapshot(int(user_id), period_from, period_to)

        metrics = {
            "wb_logistics": [
                ("finance_raw_audit.raw_json", raw.get("logistics"), int(raw.get("rows") or 0)),
                ("finance_expense_events.logistics", (events.get("logistics") or {}).get("amount"), (events.get("logistics") or {}).get("rows", 0)),
                ("expenses.logistics", (expenses.get("logistics") or {}).get("amount"), (expenses.get("logistics") or {}).get("rows", 0)),
            ],
            "wb_storage": [
                ("finance_raw_audit.raw_json", raw.get("storage"), int(raw.get("rows") or 0)),
                ("finance_expense_events.storage", (events.get("storage") or {}).get("amount"), (events.get("storage") or {}).get("rows", 0)),
                ("expenses.storage", (expenses.get("storage") or {}).get("amount"), (expenses.get("storage") or {}).get("rows", 0)),
            ],
            "wb_acquiring": [
                ("finance_raw_audit.acquiring_fee", raw.get("acquiring"), int(raw.get("rows") or 0)),
                ("finance_expense_events.acquiring", (events.get("acquiring") or {}).get("amount"), (events.get("acquiring") or {}).get("rows", 0)),
                ("expenses.acquiring", (expenses.get("acquiring") or {}).get("amount"), (expenses.get("acquiring") or {}).get("rows", 0)),
            ],
            "wb_deductions": [
                ("finance_raw_audit.deduction", raw.get("wb_deductions"), int(raw.get("rows") or 0)),
                ("finance_expense_events.wb_deductions", (events.get("wb_deductions") or {}).get("amount"), (events.get("wb_deductions") or {}).get("rows", 0)),
                ("expenses.wb_deductions", (expenses.get("wb_deductions") or {}).get("amount"), (expenses.get("wb_deductions") or {}).get("rows", 0)),
            ],
            "wb_other": [
                ("finance_raw_audit.other", raw.get("other"), int(raw.get("rows") or 0)),
                ("finance_expense_events.other", (events.get("other") or {}).get("amount"), (events.get("other") or {}).get("rows", 0)),
                ("expenses.other", (expenses.get("other") or {}).get("amount"), (expenses.get("other") or {}).get("rows", 0)),
            ],
            "penalties": [
                ("finance_raw_audit.penalty", raw.get("penalties"), int(raw.get("rows") or 0)),
                ("finance_expense_events.penalties", (events.get("penalties") or {}).get("amount"), (events.get("penalties") or {}).get("rows", 0)),
                ("expenses.penalties", (expenses.get("penalties") or {}).get("amount"), (expenses.get("penalties") or {}).get("rows", 0)),
            ],
            "advertising": [
                ("finance_expense_events.advertising", (events.get("advertising") or {}).get("amount"), (events.get("advertising") or {}).get("rows", 0)),
                ("expenses.advertising", (expenses.get("advertising") or {}).get("amount"), (expenses.get("advertising") or {}).get("rows", 0)),
            ],
            "wb_sale_amount": [
                ("finance_raw_audit.raw_json", raw.get("revenue"), int(raw.get("rows") or 0)),
                ("payment_reconciliation.sales_revenue_total", payment_snapshot.get("sales_revenue_total"), int(payment_snapshot.get("sales_rows_count") or 0)),
            ],
            "wb_payout_amount": [
                ("finance_raw_audit.raw_json", raw.get("payout"), int(raw.get("rows") or 0)),
                ("payment_reconciliation.sales_for_pay_total", payment_snapshot.get("sales_for_pay_total"), int(payment_snapshot.get("sales_rows_count") or 0)),
            ],
            "wb_total_to_pay": [
                ("finance_raw_audit.raw_json", raw.get("total_to_pay"), int(raw.get("rows") or 0)),
                ("payment_reconciliation.weekly_payout_total_all", payment_snapshot.get("weekly_payout_total_all"), int(len(payment_snapshot.get("weekly_payout_reference") or []))),
            ],
        }

        selected: dict[str, tuple[str | None, float | None, int]] = {
            metric_name: _pick_source(candidates)
            for metric_name, candidates in metrics.items()
        }
        warnings: list[str] = []
        if not raw.get("rows"):
            warnings.append("No finance_raw_audit rows in the requested weekly period.")
        if selected["wb_total_to_pay"][1] is None:
            warnings.append("WB total to pay is unavailable, parity will be approximate for payout metrics.")
        if selected["advertising"][1] is None:
            warnings.append("Advertising was not found in weekly WB-aligned expense layers.")
        if raw.get("rows") and not raw.get("logistics") and not (events.get("logistics") or {}).get("amount"):
            warnings.append("Logistics mapping coverage is incomplete for the selected week.")

        source_rows = {
            "finance_raw_audit": int(raw.get("rows") or 0),
            "finance_expense_events": int(sum(int(item.get("rows") or 0) for item in events.values())),
            "expenses": int(sum(int(item.get("rows") or 0) for item in expenses.values())),
            "sales": int((counts.get("sales_count") or 0) + (counts.get("returns_count") or 0)),
            "orders": int(counts.get("orders_count") or 0),
        }
        source_map = {
            metric_name: _source_entry(selected_source, selected_value, rows_count, metrics[metric_name])
            for metric_name, (selected_source, selected_value, rows_count) in selected.items()
        }
        source_map["finance_raw_audit"] = {
            "rows": int(raw.get("rows") or 0),
            "operation_types": dict(raw.get("operation_types") or {}),
        }
        source_map["payment_reconciliation"] = dict(payment_snapshot or {})

        snapshot = WBWeeklySnapshot(
            user_id=int(user_id),
            period_from=period_from,
            period_to=period_to,
            sales_count=int(counts.get("sales_count") or 0),
            returns_count=int(counts.get("returns_count") or 0),
            wb_sale_amount=selected["wb_sale_amount"][1],
            wb_payout_amount=selected["wb_payout_amount"][1],
            wb_logistics=selected["wb_logistics"][1],
            wb_storage=selected["wb_storage"][1],
            wb_acquiring=selected["wb_acquiring"][1],
            wb_deductions=selected["wb_deductions"][1],
            wb_other=selected["wb_other"][1],
            wb_total_to_pay=selected["wb_total_to_pay"][1],
            source_rows=source_rows,
            source_map=source_map,
            warnings=list(dict.fromkeys(warnings)),
            orders_count=int(counts.get("orders_count") or 0),
            buyouts_count=int(counts.get("sales_count") or 0),
            penalties=selected["penalties"][1],
            advertising=selected["advertising"][1],
        )
        return snapshot
    finally:
        conn.close()


def build_wb_weekly_snapshot_dict(user_id: int, period_from: date, period_to: date) -> dict[str, Any]:
    return asdict(build_wb_weekly_snapshot(int(user_id), period_from, period_to))
