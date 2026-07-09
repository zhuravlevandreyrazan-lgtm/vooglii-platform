from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Mapping
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

TRACE_REASON_CLOSED = "closed_wb_period_uses_wb_weekly_snapshot"
TRACE_REASON_OPEN = "open_period_uses_unified_operational_snapshot"
TRACE_REASON_OPEN_TOTAL_TO_PAY = "open_period_total_to_pay_matches_current_wb_payout_estimate"


class FrozenSnapshot(Mapping[str, Any]):
    def __init__(self, payload: Mapping[str, Any]):
        self._payload = dict(payload)

    def __getitem__(self, key: str) -> Any:
        return self._payload[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._payload)

    def __len__(self) -> int:
        return len(self._payload)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._payload[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __repr__(self) -> str:
        return f"FrozenSnapshot({self._payload!r})"

    def get(self, key: str, default: Any = None) -> Any:
        return self._payload.get(key, default)

    def copy(self) -> dict[str, Any]:
        return dict(self._payload)


def _freeze(value: Any) -> Any:
    if isinstance(value, FrozenSnapshot):
        return value
    if isinstance(value, Mapping):
        return FrozenSnapshot({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


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


def _trace_entry(
    value: Any,
    source_entry: Mapping[str, Any] | None,
    selected_reason: str,
    *,
    selected_source: str | None = None,
    selected_value: Any = None,
) -> dict[str, Any]:
    entry = dict(source_entry or {})
    resolved_source = selected_source if selected_source is not None else entry.get("selected_source") or entry.get("source")
    selected_table = entry.get("selected_table") or entry.get("source_table")
    selected_column = entry.get("selected_column") or entry.get("source_column")
    resolved_sum = selected_value if selected_value is not None else entry.get("selected_value", _money(value))
    return {
        "value": _money(value) if isinstance(value, (int, float)) or value is None else value,
        "selected_source": resolved_source,
        "selected_table": selected_table,
        "selected_column": selected_column,
        "selected_reason": entry.get("source_filter") or selected_reason,
        "row_count": int(entry.get("rows") or 0) if entry.get("rows") is not None else 0,
        "sum": resolved_sum,
        "source_min_date": entry.get("source_min_date"),
        "source_max_date": entry.get("source_max_date"),
    }


def _alias_trace(trace: dict[str, Any]) -> dict[str, Any]:
    return dict(trace)


def _closed_selected_value(wb_snapshot: Mapping[str, Any], field_name: str) -> float | None:
    source_map = dict(wb_snapshot.get("source_map") or {})
    source_entry = dict(source_map.get(field_name) or {})
    if "selected_value" in source_entry:
        return _money(source_entry.get("selected_value"))
    direct_value = wb_snapshot.get(field_name)
    if direct_value is not None:
        return _money(direct_value)
    return None


def _select_snapshot_value(
    *,
    use_wb_native: bool,
    wb_snapshot: Mapping[str, Any],
    wb_field_name: str,
    unified_snapshot: Mapping[str, Any],
    unified_field_name: str,
    allow_unified_fallback: bool = True,
) -> float | None:
    if use_wb_native:
        selected_value = _closed_selected_value(wb_snapshot, wb_field_name)
        if selected_value is not None:
            return selected_value
        if not allow_unified_fallback:
            return None
    return _money(unified_snapshot.get(unified_field_name))


def _selected_source_name(source_entry: Mapping[str, Any] | None) -> str:
    entry = dict(source_entry or {})
    return str(entry.get("selected_source") or entry.get("source") or "").strip()


def _is_payment_reports_missing(source_entry: Mapping[str, Any] | None) -> bool:
    return _selected_source_name(source_entry) == "payment_reports.missing"


def _sum_known(values: list[float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    if not known:
        return None
    return round(sum(known), 2)


def _derived_trace_entry(value: float | None, selected_source: str, selected_reason: str) -> dict[str, Any]:
    return _trace_entry(
        value,
        None,
        selected_reason,
        selected_source=selected_source,
        selected_value=_money(value),
    )


def _build_field_trace(
    unified_snapshot: Mapping[str, Any],
    wb_snapshot: Mapping[str, Any],
    source_mode: str,
    wb_total_to_pay: float | None,
    advertising_value: float | None,
    operational_profit: float | None,
    cost_price: float | None,
    other_expenses: float | None,
    penalties: float | None,
    expenses_total: float | None,
    operational_reason: str,
    expenses_total_reason: str,
) -> dict[str, Any]:
    unified_sources = dict(unified_snapshot.get("source_map") or unified_snapshot.get("debug_sources") or {})
    wb_sources = dict(wb_snapshot.get("source_map") or {})
    use_wb = source_mode == "WB_NATIVE_CLOSED"

    wb_sale_amount = _select_snapshot_value(
        use_wb_native=use_wb,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_sale_amount",
        unified_snapshot=unified_snapshot,
        unified_field_name="sales_revenue",
    )
    wb_payout_amount = _select_snapshot_value(
        use_wb_native=use_wb,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_payout_amount",
        unified_snapshot=unified_snapshot,
        unified_field_name="wb_payout",
    )
    wb_logistics = _select_snapshot_value(
        use_wb_native=use_wb,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_logistics",
        unified_snapshot=unified_snapshot,
        unified_field_name="logistics",
        allow_unified_fallback=False,
    )
    wb_storage = _select_snapshot_value(
        use_wb_native=use_wb,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_storage",
        unified_snapshot=unified_snapshot,
        unified_field_name="storage",
        allow_unified_fallback=False,
    )
    wb_acquiring = _select_snapshot_value(
        use_wb_native=use_wb,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_acquiring",
        unified_snapshot=unified_snapshot,
        unified_field_name="acquiring",
    )
    wb_deductions = _select_snapshot_value(
        use_wb_native=use_wb,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_deductions",
        unified_snapshot=unified_snapshot,
        unified_field_name="wb_deductions",
    )

    reason = TRACE_REASON_CLOSED if use_wb else TRACE_REASON_OPEN
    expenses_trace = (
        _derived_trace_entry(expenses_total, "derived_sum", expenses_total_reason)
        if use_wb
        else _trace_entry(expenses_total, unified_sources.get("expenses_total"), expenses_total_reason)
    )
    operational_trace = (
        _derived_trace_entry(operational_profit, "derived_sales_revenue_minus_expenses_total", operational_reason)
        if use_wb
        else _trace_entry(operational_profit, unified_sources.get("profit_before_tax"), operational_reason)
    )
    field_trace = {
        "wb_sale_amount": _trace_entry(wb_sale_amount, wb_sources.get("wb_sale_amount") if use_wb else unified_sources.get("sales_revenue"), reason),
        "sales_revenue": _trace_entry(wb_sale_amount, wb_sources.get("wb_sale_amount") if use_wb else unified_sources.get("sales_revenue"), reason),
        "wb_payout_amount": _trace_entry(wb_payout_amount, wb_sources.get("wb_payout_amount") if use_wb else unified_sources.get("wb_payout"), reason),
        "wb_payout": _trace_entry(wb_payout_amount, wb_sources.get("wb_payout_amount") if use_wb else unified_sources.get("wb_payout"), reason),
        "wb_total_to_pay": _trace_entry(
            wb_total_to_pay,
            wb_sources.get("wb_total_to_pay") if use_wb else unified_sources.get("wb_payout"),
            TRACE_REASON_CLOSED if use_wb else TRACE_REASON_OPEN_TOTAL_TO_PAY,
        ),
        "wb_logistics": _trace_entry(wb_logistics, wb_sources.get("wb_logistics") if use_wb else unified_sources.get("logistics"), reason),
        "logistics": _trace_entry(wb_logistics, wb_sources.get("wb_logistics") if use_wb else unified_sources.get("logistics"), reason),
        "wb_storage": _trace_entry(wb_storage, wb_sources.get("wb_storage") if use_wb else unified_sources.get("storage"), reason),
        "storage": _trace_entry(wb_storage, wb_sources.get("wb_storage") if use_wb else unified_sources.get("storage"), reason),
        "wb_acquiring": _trace_entry(wb_acquiring, wb_sources.get("wb_acquiring") if use_wb else unified_sources.get("acquiring"), reason),
        "acquiring": _trace_entry(wb_acquiring, wb_sources.get("wb_acquiring") if use_wb else unified_sources.get("acquiring"), reason),
        "wb_deductions": _trace_entry(wb_deductions, wb_sources.get("wb_deductions") if use_wb else unified_sources.get("wb_deductions"), reason),
        "advertising": _trace_entry(advertising_value, wb_sources.get("advertising") if use_wb else unified_sources.get("advertising_spend"), reason),
        "advertising_spend": _trace_entry(advertising_value, wb_sources.get("advertising") if use_wb else unified_sources.get("advertising_spend"), reason),
        "cost_price": _trace_entry(cost_price, unified_sources.get("cost_price"), "customer_snapshot_uses_unified_cost_price"),
        "other_expenses": _trace_entry(other_expenses, wb_sources.get("wb_other") if use_wb else unified_sources.get("other_expenses"), reason),
        "wb_other": _trace_entry(other_expenses, wb_sources.get("wb_other") if use_wb else unified_sources.get("other_expenses"), reason),
        "penalties": _trace_entry(penalties, wb_sources.get("penalties") if use_wb else unified_sources.get("penalties"), reason),
        "expenses_total": expenses_trace,
        "operational_profit": operational_trace,
        "profit_before_tax": operational_trace,
        "net_profit": _trace_entry(unified_snapshot.get("net_profit"), unified_sources.get("net_profit"), "customer_snapshot_uses_unified_net_profit"),
    }
    return {key: _alias_trace(value) for key, value in field_trace.items()}


def build_customer_financial_snapshot(user_id: int, period_from: date, period_to: date, *, bot=None) -> FrozenSnapshot:
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

    use_wb_native = period_info["status"] == PERIOD_CLOSED
    wb_snapshot = build_wb_weekly_snapshot_dict(int(user_id), period_from, period_to) if use_wb_native else {}
    source_mode = "WB_NATIVE_CLOSED" if use_wb_native else "OPERATIONAL_PRELIMINARY"
    is_preliminary = not use_wb_native

    wb_sale_amount = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_sale_amount",
        unified_snapshot=unified,
        unified_field_name="sales_revenue",
    )
    wb_payout_amount = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_payout_amount",
        unified_snapshot=unified,
        unified_field_name="wb_payout",
    )
    wb_total_to_pay = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_total_to_pay",
        unified_snapshot=unified,
        unified_field_name="wb_payout",
        allow_unified_fallback=False,
    )
    wb_logistics = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_logistics",
        unified_snapshot=unified,
        unified_field_name="logistics",
        allow_unified_fallback=False,
    )
    wb_storage = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_storage",
        unified_snapshot=unified,
        unified_field_name="storage",
        allow_unified_fallback=False,
    )
    wb_acquiring = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_acquiring",
        unified_snapshot=unified,
        unified_field_name="acquiring",
    )
    wb_deductions = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_deductions",
        unified_snapshot=unified,
        unified_field_name="wb_deductions",
    )
    wb_other = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="wb_other",
        unified_snapshot=unified,
        unified_field_name="other_expenses",
    )
    advertising = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="advertising",
        unified_snapshot=unified,
        unified_field_name="advertising_spend",
    )
    cost_price = unified.get("cost_price")
    penalties = _select_snapshot_value(
        use_wb_native=use_wb_native,
        wb_snapshot=wb_snapshot,
        wb_field_name="penalties",
        unified_snapshot=unified,
        unified_field_name="penalties",
    )

    if use_wb_native:
        operational_expenses_total = _sum_known(
            [
                _money(cost_price),
                _money(advertising),
                _money(wb_logistics),
                _money(wb_storage),
                _money(wb_acquiring),
                _money(wb_deductions),
                _money(wb_other),
                _money(penalties),
            ]
        )
        operational_profit = (
            round(float(wb_sale_amount) - float(operational_expenses_total), 2)
            if wb_sale_amount is not None and operational_expenses_total is not None
            else None
        )
        margin_percent = (
            round(float(operational_profit) / float(wb_sale_amount) * 100, 1)
            if operational_profit is not None and wb_sale_amount not in (None, 0)
            else None
        )
        roi_base = _sum_known([_money(cost_price), _money(advertising)])
        roi_percent = (
            round(float(operational_profit) / float(roi_base) * 100, 1)
            if operational_profit is not None and roi_base not in (None, 0)
            else None
        )
    else:
        operational_expenses_total = _money(unified.get("expenses_total"))
        operational_profit = _money(unified.get("profit_before_tax"))
        margin_percent = _money(unified.get("margin_percent"))
        roi_percent = _money(unified.get("roi_percent"))

    tax_amount = _money(unified.get("tax_amount"))
    net_profit = (
        round(float(operational_profit) - float(tax_amount), 2)
        if use_wb_native and operational_profit is not None and tax_amount is not None
        else (None if use_wb_native else _money(unified.get("net_profit")))
    )

    closed_week_ready = (
        use_wb_native
        and all(
            value is not None
            for value in (
                wb_sale_amount,
                cost_price,
                advertising,
                wb_logistics,
                wb_storage,
                wb_acquiring,
                wb_deductions,
            )
        )
        and not _is_payment_reports_missing((wb_snapshot.get("source_map") or {}).get("wb_logistics"))
        and not _is_payment_reports_missing((wb_snapshot.get("source_map") or {}).get("wb_storage"))
    )

    finance_status = "FINANCE_OK" if closed_week_ready else unified.get("finance_status")
    finance_confidence = "HIGH" if closed_week_ready else unified.get("finance_confidence")
    finance_confidence_score = 95 if closed_week_ready else unified.get("finance_confidence_score")
    finance_confidence_reason = (
        "Closed weekly WB period uses customer snapshot P&L breakdown."
        if closed_week_ready
        else unified.get("finance_confidence_reason")
    )
    profit_display_mode = "FINAL" if closed_week_ready else unified.get("profit_display_mode")

    field_trace = _build_field_trace(
        unified,
        wb_snapshot,
        source_mode,
        _money(wb_total_to_pay),
        _money(advertising),
        _money(operational_profit),
        _money(cost_price),
        _money(wb_other),
        _money(penalties),
        _money(operational_expenses_total),
        "closed_customer_snapshot_formula" if use_wb_native else "customer_snapshot_uses_unified_operational_profit",
        "closed_customer_snapshot_expense_sum" if use_wb_native else "customer_snapshot_uses_operational_expenses_total",
    )

    warnings = list(unified.get("warnings") or [])
    if use_wb_native:
        warnings = [
            item
            for item in warnings
            if "official net profit" not in str(item).lower()
            and "ещё не подтверждены" not in str(item).lower()
            and "подтверждены полностью" not in str(item).lower()
        ]
        if tax_amount is None:
            warnings.append("Налоговый режим не настроен. Чистая прибыль после налога не рассчитана.")

    payload = {
        **dict(unified),
        "source_mode": source_mode,
        "is_preliminary": is_preliminary,
        "sales_count": wb_snapshot.get("sales_count") if use_wb_native else unified.get("sales_count"),
        "returns_count": wb_snapshot.get("returns_count") if use_wb_native else unified.get("returns_count"),
        "buyouts_count": wb_snapshot.get("buyouts_count") if use_wb_native else unified.get("buyouts_count"),
        "orders_count": wb_snapshot.get("orders_count") if use_wb_native else unified.get("orders_count"),
        "sales_revenue": _money(wb_sale_amount),
        "wb_sale_amount": _money(wb_sale_amount),
        "wb_payout": _money(wb_payout_amount),
        "wb_payout_amount": _money(wb_payout_amount),
        "wb_total_to_pay": _money(wb_total_to_pay),
        "logistics": _money(wb_logistics),
        "wb_logistics": _money(wb_logistics),
        "storage": _money(wb_storage),
        "wb_storage": _money(wb_storage),
        "acquiring": _money(wb_acquiring),
        "wb_acquiring": _money(wb_acquiring),
        "wb_deductions": _money(wb_deductions),
        "other_expenses": _money(wb_other),
        "wb_other": _money(wb_other),
        "penalties": _money(penalties),
        "advertising_spend": _money(advertising),
        "advertising": _money(advertising),
        "cost_price": _money(cost_price),
        "operational_profit": _money(operational_profit),
        "operational_estimate": _money(operational_profit),
        "profit_before_tax": _money(operational_profit),
        "tax_amount": tax_amount,
        "net_profit": _money(net_profit),
        "official_net_profit": None if use_wb_native else _money(unified.get("official_net_profit")),
        "expenses_total": _money(operational_expenses_total),
        "margin_percent": margin_percent,
        "roi_percent": roi_percent,
        "finance_status": finance_status,
        "finance_confidence": finance_confidence,
        "finance_confidence_score": finance_confidence_score,
        "finance_confidence_reason": finance_confidence_reason,
        "profit_display_mode": profit_display_mode,
        "period_status": period_info["status"],
        "period_status_source": period_info["source"],
        "period_status_confidence": period_info["confidence"],
        "wb_data_status_text": _wb_data_status_text(period_info["status"], (same_period_validation or {}).get("status")),
        "wb_native_snapshot": _freeze(wb_snapshot),
        "operational_snapshot": _freeze(dict(unified)),
        "validation_status": (same_period_validation or {}).get("status"),
        "validation_score": _money((same_period_validation or {}).get("parity_score")),
        "warnings": tuple(warnings),
        "field_trace": _freeze(field_trace),
        "financial_trace": _freeze(field_trace),
    }
    return _freeze(payload)


def build_customer_financial_snapshot_dict(user_id: int, days, *, bot=None) -> FrozenSnapshot:
    period_from, period_to = _to_dates(days)
    return build_customer_financial_snapshot(int(user_id), period_from, period_to, bot=bot)


def build_customer_snapshot(user_id: int, days, *, bot=None) -> FrozenSnapshot:
    return build_customer_financial_snapshot_dict(int(user_id), days, bot=bot)
