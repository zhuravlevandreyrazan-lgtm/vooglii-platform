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
)
RAW_STORAGE_KEYS = ("storage_fee",)
RAW_REVENUE_KEYS = ("retail_amount",)
RAW_PAYOUT_KEYS = ("ppvz_for_pay",)
RAW_TOTAL_TO_PAY_KEYS = ("ppvz_for_pay",)


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


def _pick_row_key(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        amount = _money(payload.get(key))
        if amount is not None:
            return abs(amount)
    return None


def _sum_values(values: list[float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    if not known:
        return None
    return round(sum(known), 2)


def _sum_payment_rows(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [_money((row or {}).get(key)) for row in rows]
    return _sum_values(values)


def _pick_source(candidates: list[tuple[str, float | None, int]]) -> tuple[str | None, float | None, int]:
    fallback: tuple[str | None, float | None, int] = (None, None, 0)
    for source_name, value, rows in candidates:
        if value is None:
            continue
        return source_name, _money(value), int(rows or 0)
    return fallback


def _candidate(
    source_name: str,
    value: float | None,
    rows: int,
    *,
    source_table: str,
    source_column: str,
    source_filter: str,
    source_min_date: str | None = None,
    source_max_date: str | None = None,
    breakdown: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": source_name,
        "value": _money(value),
        "rows": int(rows or 0),
        "source_table": source_table,
        "source_column": source_column,
        "source_filter": source_filter,
        "source_min_date": source_min_date,
        "source_max_date": source_max_date,
        "breakdown": dict(breakdown or {}),
    }


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
    min_date = str(rows[0]["report_date"])[:10] if rows else None
    max_date = str(rows[-1]["report_date"])[:10] if rows else None
    for row in rows:
        payload = {}
        try:
            payload = json.loads(str(row["raw_json"] or "") or "{}")
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            raw_logistics_values.append(_sum_row_keys(payload, RAW_LOGISTICS_KEYS))
            raw_storage_values.append(_sum_row_keys(payload, RAW_STORAGE_KEYS))
            raw_revenue_values.append(_pick_row_key(payload, RAW_REVENUE_KEYS))
            raw_payout_values.append(_pick_row_key(payload, RAW_PAYOUT_KEYS))
            raw_total_to_pay_values.append(_pick_row_key(payload, RAW_TOTAL_TO_PAY_KEYS))
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
        "min_date": min_date,
        "max_date": max_date,
    }
    return summary


def _source_entry(selected_source: str | None, selected_value: float | int | None, rows: int, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    selected_candidate = next((item for item in candidates if item.get("source") == selected_source), {})
    return {
        "selected_source": selected_source,
        "selected_value": selected_value,
        "rows": int(rows or 0),
        "source_table": selected_candidate.get("source_table"),
        "source_column": selected_candidate.get("source_column"),
        "source_filter": selected_candidate.get("source_filter"),
        "source_min_date": selected_candidate.get("source_min_date"),
        "source_max_date": selected_candidate.get("source_max_date"),
        "breakdown": dict(selected_candidate.get("breakdown") or {}),
        "candidates": [dict(item) for item in candidates],
    }


def _missing_source_entry(
    *,
    source_name: str,
    source_table: str,
    source_column: str,
    source_filter: str,
    source_min_date: str | None,
    source_max_date: str | None,
    rows: int,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "selected_source": source_name,
        "selected_value": None,
        "rows": int(rows or 0),
        "source_table": source_table,
        "source_column": source_column,
        "source_filter": source_filter,
        "source_min_date": source_min_date,
        "source_max_date": source_max_date,
        "breakdown": {},
        "candidates": [dict(item) for item in candidates],
    }


def build_wb_weekly_snapshot(user_id: int, period_from: date, period_to: date) -> WBWeeklySnapshot:
    conn = _connect()
    try:
        counts = _fetch_sales_counts(conn, int(user_id), period_from, period_to)
        raw = _build_raw_summary(conn, int(user_id), period_from, period_to)
        events = _fetch_grouped_events(conn, int(user_id), period_from, period_to)
        expenses = _fetch_grouped_expenses(conn, int(user_id), period_from, period_to)
        payment_snapshot = _fetch_payment_snapshot(int(user_id), period_from, period_to)
        payment_source = str(payment_snapshot.get("payment_reports_source") or "").strip()
        payment_status = str(payment_snapshot.get("payment_reports_status") or "").strip()

        payment_rows = [
            row
            for row in list(payment_snapshot.get("payment_reports_rows") or [])
            if str(row.get("period_start") or "")[:10] <= str(period_to)
            and str(row.get("period_end") or "")[:10] >= str(period_from)
        ]
        payment_total_revenue = _money(payment_snapshot.get("payment_reports_total_revenue")) if payment_rows else None
        payment_total_for_pay = _money(payment_snapshot.get("payment_reports_total_for_pay")) if payment_rows else None
        payment_total_bank_payment = _money(payment_snapshot.get("payment_reports_total_bank_payment")) if payment_rows else None
        payment_total_delivery = _money(payment_snapshot.get("payment_reports_total_delivery")) if payment_rows else None
        payment_total_storage = _money(payment_snapshot.get("payment_reports_total_storage")) if payment_rows else None
        payment_total_deduction = _money(payment_snapshot.get("payment_reports_total_deduction")) if payment_rows else None
        if payment_rows:
            payment_total_revenue = payment_total_revenue if payment_total_revenue not in (None, 0.0) else _sum_payment_rows(payment_rows, "revenue")
            payment_total_for_pay = payment_total_for_pay if payment_total_for_pay not in (None, 0.0) else _sum_payment_rows(payment_rows, "for_pay")
            payment_total_bank_payment = payment_total_bank_payment if payment_total_bank_payment not in (None, 0.0) else _sum_payment_rows(payment_rows, "bank_payment")
            payment_total_delivery = payment_total_delivery if payment_total_delivery not in (None, 0.0) else _sum_payment_rows(payment_rows, "delivery")
            payment_total_storage = payment_total_storage if payment_total_storage not in (None, 0.0) else _sum_payment_rows(payment_rows, "storage")
            payment_total_deduction = payment_total_deduction if payment_total_deduction not in (None, 0.0) else _sum_payment_rows(payment_rows, "deduction")
        payment_breakdown = {
            str(item.get("type") or "unknown"): int(
                sum(1 for row in payment_rows if str(row.get("type") or "unknown") == str(item.get("type") or "unknown"))
            )
            for item in payment_rows
        }
        payment_min_date = min(
            [str(item.get("period_start") or "")[:10] for item in payment_rows if str(item.get("period_start") or "").strip()],
            default=None,
        )
        payment_max_date = max(
            [str(item.get("period_end") or "")[:10] for item in payment_rows if str(item.get("period_end") or "").strip()],
            default=None,
        )
        weekly_filter = f"period overlaps {period_from}..{period_to}"
        raw_filter = f"telegram_id={int(user_id)} AND report_date BETWEEN {period_from} AND {period_to}"
        metrics = {
            "wb_logistics": [
                _candidate(
                    "payment_reports.delivery",
                    payment_total_delivery,
                    len(payment_rows),
                    source_table="payment_reports_rows",
                    source_column="delivery",
                    source_filter=weekly_filter,
                    source_min_date=payment_min_date,
                    source_max_date=payment_max_date,
                    breakdown=payment_breakdown,
                ),
                _candidate(
                    "finance_raw_audit.raw_json",
                    raw.get("logistics"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="raw_json.delivery_rub|rebill_logistic_cost|return_amount|delivery_amount",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
                _candidate(
                    "finance_expense_events.logistics",
                    (events.get("logistics") or {}).get("amount"),
                    (events.get("logistics") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=logistics AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.logistics",
                    (expenses.get("logistics") or {}).get("amount"),
                    (expenses.get("logistics") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=logistics AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "wb_storage": [
                _candidate(
                    "payment_reports.storage",
                    payment_total_storage,
                    len(payment_rows),
                    source_table="payment_reports_rows",
                    source_column="storage",
                    source_filter=weekly_filter,
                    source_min_date=payment_min_date,
                    source_max_date=payment_max_date,
                    breakdown=payment_breakdown,
                ),
                _candidate(
                    "finance_raw_audit.raw_json",
                    raw.get("storage"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="raw_json.storage_fee|storage|storage_cost",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
                _candidate(
                    "finance_expense_events.storage",
                    (events.get("storage") or {}).get("amount"),
                    (events.get("storage") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=storage AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.storage",
                    (expenses.get("storage") or {}).get("amount"),
                    (expenses.get("storage") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=storage AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "wb_acquiring": [
                _candidate(
                    "finance_raw_audit.acquiring_fee",
                    raw.get("acquiring"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="acquiring_fee",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
                _candidate(
                    "finance_expense_events.acquiring",
                    (events.get("acquiring") or {}).get("amount"),
                    (events.get("acquiring") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=acquiring AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.acquiring",
                    (expenses.get("acquiring") or {}).get("amount"),
                    (expenses.get("acquiring") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=acquiring AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "wb_deductions": [
                _candidate(
                    "payment_reports.deduction",
                    payment_total_deduction,
                    len(payment_rows),
                    source_table="payment_reports_rows",
                    source_column="deduction",
                    source_filter=weekly_filter,
                    source_min_date=payment_min_date,
                    source_max_date=payment_max_date,
                    breakdown=payment_breakdown,
                ),
                _candidate(
                    "finance_raw_audit.deduction",
                    raw.get("wb_deductions"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="deduction",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
                _candidate(
                    "finance_expense_events.wb_deductions",
                    (events.get("wb_deductions") or {}).get("amount"),
                    (events.get("wb_deductions") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=wb_deductions AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.wb_deductions",
                    (expenses.get("wb_deductions") or {}).get("amount"),
                    (expenses.get("wb_deductions") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=wb_deductions AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "wb_other": [
                _candidate(
                    "finance_raw_audit.other",
                    raw.get("other"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="penalty|acceptance|acceptance_fee|additional_payment",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
                _candidate(
                    "finance_expense_events.other",
                    (events.get("other") or {}).get("amount"),
                    (events.get("other") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=other AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.other",
                    (expenses.get("other") or {}).get("amount"),
                    (expenses.get("other") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=other AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "penalties": [
                _candidate(
                    "finance_raw_audit.penalty",
                    raw.get("penalties"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="penalty",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
                _candidate(
                    "finance_expense_events.penalties",
                    (events.get("penalties") or {}).get("amount"),
                    (events.get("penalties") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=penalties AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.penalties",
                    (expenses.get("penalties") or {}).get("amount"),
                    (expenses.get("penalties") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=penalties AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "advertising": [
                _candidate(
                    "finance_expense_events.advertising",
                    (events.get("advertising") or {}).get("amount"),
                    (events.get("advertising") or {}).get("rows", 0),
                    source_table="finance_expense_events",
                    source_column="amount",
                    source_filter=f"expense_category=advertising AND event_date BETWEEN {period_from} AND {period_to}",
                ),
                _candidate(
                    "expenses.advertising",
                    (expenses.get("advertising") or {}).get("amount"),
                    (expenses.get("advertising") or {}).get("rows", 0),
                    source_table="expenses",
                    source_column="amount",
                    source_filter=f"expense_type=advertising AND expense_date BETWEEN {period_from} AND {period_to}",
                ),
            ],
            "wb_sale_amount": [
                _candidate(
                    "payment_reports.revenue",
                    payment_total_revenue,
                    len(payment_rows),
                    source_table="payment_reports_rows",
                    source_column="revenue",
                    source_filter=weekly_filter,
                    source_min_date=payment_min_date,
                    source_max_date=payment_max_date,
                    breakdown=payment_breakdown,
                ),
                _candidate(
                    "finance_raw_audit.raw_json",
                    raw.get("revenue"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="raw_json.sale_amount|retail_amount|retail_price_withdisc_rub",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
            ],
            "wb_payout_amount": [
                _candidate(
                    "payment_reports.for_pay",
                    payment_total_for_pay,
                    len(payment_rows),
                    source_table="payment_reports_rows",
                    source_column="for_pay",
                    source_filter=weekly_filter,
                    source_min_date=payment_min_date,
                    source_max_date=payment_max_date,
                    breakdown=payment_breakdown,
                ),
                _candidate(
                    "finance_raw_audit.raw_json",
                    raw.get("payout"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="raw_json.ppvz_for_pay|supplier_operating_reward|supplier_payment|to_pay|payment_amount",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
            ],
            "wb_total_to_pay": [
                _candidate(
                    "payment_reports.bank_payment",
                    payment_total_bank_payment,
                    len(payment_rows),
                    source_table="payment_reports_rows",
                    source_column="bank_payment",
                    source_filter=weekly_filter,
                    source_min_date=payment_min_date,
                    source_max_date=payment_max_date,
                    breakdown=payment_breakdown,
                ),
                _candidate(
                    "finance_raw_audit.raw_json",
                    raw.get("total_to_pay"),
                    int(raw.get("rows") or 0),
                    source_table="finance_raw_audit",
                    source_column="raw_json.ppvz_for_pay|to_pay|payment_amount",
                    source_filter=raw_filter,
                    source_min_date=raw.get("min_date"),
                    source_max_date=raw.get("max_date"),
                    breakdown=raw.get("operation_types"),
                ),
            ],
        }

        selected: dict[str, tuple[str | None, float | None, int]] = {
            metric_name: _pick_source([(item["source"], item["value"], item["rows"]) for item in candidates])
            for metric_name, candidates in metrics.items()
        }
        warnings: list[str] = []
        if not raw.get("rows"):
            warnings.append("No finance_raw_audit rows in the requested weekly period.")
        if payment_source != "wb_api":
            warnings.append(f"payment_reports_rows unavailable: source={payment_source or 'unknown'} status={payment_status or 'UNKNOWN'}")
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
        for metric_name, source_column in {
            "wb_logistics": "delivery",
            "wb_storage": "storage",
            "wb_total_to_pay": "bank_payment",
        }.items():
            details = dict(source_map.get(metric_name) or {})
            if str(details.get("selected_source") or "").startswith("payment_reports.") and details.get("selected_value") is not None:
                continue
            source_map[metric_name] = _missing_source_entry(
                source_name="payment_reports.missing",
                source_table="payment_reports_rows",
                source_column=source_column,
                source_filter=weekly_filter,
                source_min_date=payment_min_date,
                source_max_date=payment_max_date,
                rows=len(payment_rows),
                candidates=metrics[metric_name],
            )
        if source_map["wb_total_to_pay"].get("selected_value") is None:
            warnings.append("WB total to pay is unavailable, parity will be approximate for payout metrics.")
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
            wb_logistics=source_map["wb_logistics"].get("selected_value"),
            wb_storage=source_map["wb_storage"].get("selected_value"),
            wb_acquiring=selected["wb_acquiring"][1],
            wb_deductions=selected["wb_deductions"][1],
            wb_other=selected["wb_other"][1],
            wb_total_to_pay=source_map["wb_total_to_pay"].get("selected_value"),
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
