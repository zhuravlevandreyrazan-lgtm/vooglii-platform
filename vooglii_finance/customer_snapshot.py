from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

import config
from db_manager import init_db

from vooglii_validation.validator import get_latest_validation_result
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot_dict

from .unified_snapshot import build_unified_financial_snapshot_dict


PERIOD_OPEN = "OPEN"
PERIOD_CLOSED = "CLOSED"
PERIOD_PARTIAL = "PARTIAL"
PERIOD_UNKNOWN = "UNKNOWN"


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _month_bounds(value: date) -> tuple[date, date]:
    month_start = value.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    return month_start, next_month - timedelta(days=1)


def _to_dates(days) -> tuple[date, date]:
    if isinstance(days, tuple) and len(days) == 2:
        return date.fromisoformat(str(days[0])), date.fromisoformat(str(days[1]))
    if isinstance(days, list) and len(days) == 2:
        return date.fromisoformat(str(days[0])), date.fromisoformat(str(days[1]))

    normalized = str(days or "").strip().lower()
    today = date.today()
    if normalized == "today":
        return today, today
    if normalized in {"week", "last_7_days"}:
        return today - timedelta(days=6), today
    if normalized in {"month", "last_30_days"}:
        return today - timedelta(days=29), today
    if normalized == "current_month":
        period_from, _ = _month_bounds(today)
        return period_from, today
    if normalized == "previous_month":
        previous_month_day = today.replace(day=1) - timedelta(days=1)
        return _month_bounds(previous_month_day)
    raise ValueError("days must be a supported period keyword or a (period_from, period_to) tuple")


def _money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _is_week_window(period_from: date, period_to: date) -> bool:
    return period_from.weekday() == 0 and period_to.weekday() == 6 and (period_to - period_from).days == 6


def _derive_period_status(user_id: int, period_from: date, period_to: date) -> tuple[str, str, str]:
    conn = _connect()
    try:
        raw_row = conn.execute(
            """
            SELECT COUNT(*) AS rows_count
            FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date, 1, 10) BETWEEN ? AND ?
            """,
            (int(user_id), str(period_from), str(period_to)),
        ).fetchone()
        event_row = conn.execute(
            """
            SELECT COUNT(*) AS rows_count
            FROM finance_expense_events
            WHERE user_id=? AND substr(event_date, 1, 10) BETWEEN ? AND ?
            """,
            (int(user_id), str(period_from), str(period_to)),
        ).fetchone()
    finally:
        conn.close()

    raw_rows = int(raw_row["rows_count"] or 0) if raw_row else 0
    event_rows = int(event_row["rows_count"] or 0) if event_row else 0
    today = date.today()
    if _is_week_window(period_from, period_to) and period_to < today and raw_rows > 0:
        return PERIOD_CLOSED, "finance_raw_audit", "high"
    if raw_rows > 0 or event_rows > 0:
        if period_to >= today:
            return PERIOD_OPEN, "runtime_activity", "medium"
        return PERIOD_PARTIAL, "partial_finance_rows", "medium"
    if period_to >= today:
        return PERIOD_OPEN, "current_period", "low"
    return PERIOD_UNKNOWN, "no_finance_rows", "low"


def refresh_wb_financial_period(user_id: int, period_from: date, period_to: date) -> dict[str, Any]:
    status, source, confidence = _derive_period_status(int(user_id), period_from, period_to)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO wb_financial_periods(user_id, period_from, period_to, status, source, confidence, created_at, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id, period_from, period_to)
            DO UPDATE SET
                status=excluded.status,
                source=excluded.source,
                confidence=excluded.confidence,
                updated_at=excluded.updated_at
            """,
            (int(user_id), str(period_from), str(period_to), status, source, confidence, now_text, now_text),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "user_id": int(user_id),
        "period_from": str(period_from),
        "period_to": str(period_to),
        "status": status,
        "source": source,
        "confidence": confidence,
    }


def _wb_data_status_text(period_status: str, validation_status: str | None) -> str:
    normalized_validation = str(validation_status or "").upper()
    if normalized_validation in {"FAIL", "WARN"}:
        return "Данные WB: 🔴 есть расхождения"
    if period_status == PERIOD_CLOSED:
        return "Данные WB: 🟢 период закрыт"
    if period_status == PERIOD_PARTIAL:
        return "Данные WB: 🟡 часть финансов ещё обновляется"
    if period_status == PERIOD_OPEN:
        return "Данные WB: 🟡 данные обновляются"
    return "Данные WB: 🟡 данные обновляются"


def build_customer_financial_snapshot(user_id: int, period_from: date, period_to: date, *, bot=None) -> dict[str, Any]:
    unified = build_unified_financial_snapshot_dict(int(user_id), (str(period_from), str(period_to)), bot=bot)
    period_info = refresh_wb_financial_period(int(user_id), period_from, period_to)
    latest_validation = get_latest_validation_result(int(user_id))
    same_period_validation = (
        latest_validation
        if latest_validation
        and str(latest_validation.get("period_from") or "") == str(period_from)
        and str(latest_validation.get("period_to") or "") == str(period_to)
        else None
    )

    if period_info["status"] == PERIOD_CLOSED:
        wb_snapshot = build_wb_weekly_snapshot_dict(int(user_id), period_from, period_to)
        primary = {
            "source_mode": "WB_NATIVE_CLOSED",
            "is_preliminary": False,
            "sales_count": wb_snapshot.get("sales_count"),
            "returns_count": wb_snapshot.get("returns_count"),
            "buyouts_count": wb_snapshot.get("buyouts_count"),
            "orders_count": wb_snapshot.get("orders_count"),
            "sales_revenue": wb_snapshot.get("wb_sale_amount"),
            "wb_payout": wb_snapshot.get("wb_payout_amount"),
            "wb_total_to_pay": wb_snapshot.get("wb_total_to_pay"),
            "logistics": wb_snapshot.get("wb_logistics"),
            "storage": wb_snapshot.get("wb_storage"),
            "acquiring": wb_snapshot.get("wb_acquiring"),
            "wb_deductions": wb_snapshot.get("wb_deductions"),
            "other_expenses": wb_snapshot.get("wb_other"),
            "advertising_spend": wb_snapshot.get("advertising"),
        }
    else:
        wb_snapshot = {}
        primary = {
            "source_mode": "OPERATIONAL_PRELIMINARY",
            "is_preliminary": True,
            "sales_count": unified.get("sales_count"),
            "returns_count": unified.get("returns_count"),
            "buyouts_count": unified.get("buyouts_count"),
            "orders_count": unified.get("orders_count"),
            "sales_revenue": unified.get("sales_revenue"),
            "wb_payout": unified.get("wb_payout"),
            "wb_total_to_pay": unified.get("wb_payout"),
            "logistics": unified.get("logistics"),
            "storage": unified.get("storage"),
            "acquiring": unified.get("acquiring"),
            "wb_deductions": unified.get("wb_deductions"),
            "other_expenses": unified.get("other_expenses"),
            "advertising_spend": unified.get("advertising_spend"),
        }

    snapshot = dict(unified)
    snapshot.update(primary)
    snapshot["period_status"] = period_info["status"]
    snapshot["period_status_source"] = period_info["source"]
    snapshot["period_status_confidence"] = period_info["confidence"]
    snapshot["wb_data_status_text"] = _wb_data_status_text(period_info["status"], (same_period_validation or {}).get("status"))
    snapshot["wb_native_snapshot"] = wb_snapshot
    snapshot["operational_snapshot"] = dict(unified)
    snapshot["validation_status"] = (same_period_validation or {}).get("status")
    snapshot["validation_score"] = _money((same_period_validation or {}).get("parity_score"))
    snapshot["operational_estimate"] = unified.get("profit_before_tax")
    return snapshot


def build_customer_financial_snapshot_dict(user_id: int, days, *, bot=None) -> dict[str, Any]:
    period_from, period_to = _to_dates(days)
    return build_customer_financial_snapshot(int(user_id), period_from, period_to, bot=bot)
