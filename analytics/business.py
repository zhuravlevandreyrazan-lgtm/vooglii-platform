from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

import telegram_bot

from config import DB_NAME
from analytics.common import DEFAULT_USER_ID, current_month_days, route_for_workspace, safe_float, safe_int, safe_text, snapshot_context, status_to_severity, status_to_tone


NO_BUSINESS_DATA_STATUS = "No business data available"


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = safe_float(value)
        if parsed is not None:
            return parsed
    return None


def _today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _days_window(days: int) -> tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=max(days - 1, 0))
    return start.isoformat(), end.isoformat()


def _sqlite_business_aggregate(user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
    result = {
        "sales_rows": 0,
        "units_sold": 0,
        "returns": 0,
        "sales_revenue": None,
        "order_rows": 0,
        "orders": 0,
        "cancelled_orders": 0,
        "orders_revenue": None,
        "available": False,
    }

    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute(
            "SELECT "
            "COUNT(*), "
            "SUM(CASE WHEN COALESCE(is_return,0)=0 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN COALESCE(is_return,0)=1 THEN 1 ELSE 0 END), "
            "COALESCE(SUM(CASE WHEN COALESCE(is_return,0)=0 THEN COALESCE(price_with_disc,0) ELSE 0 END),0) "
            "FROM sales WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?",
            (user_id, start_date, end_date),
        )
        sales_row = cur.fetchone() or (0, 0, 0, 0)

        cur.execute(
            "SELECT "
            "COUNT(*), "
            "COUNT(DISTINCT CASE "
            "WHEN COALESCE(is_cancel,0)=0 AND LENGTH(TRIM(COALESCE(order_id,''))) > 0 THEN order_id "
            "END), "
            "SUM(CASE WHEN COALESCE(is_cancel,0)=1 THEN 1 ELSE 0 END), "
            "COALESCE(SUM(CASE WHEN COALESCE(is_cancel,0)=0 THEN COALESCE(price_with_disc,0) ELSE 0 END),0) "
            "FROM orders WHERE telegram_id=? AND substr(order_date,1,10) BETWEEN ? AND ?",
            (user_id, start_date, end_date),
        )
        orders_row = cur.fetchone() or (0, 0, 0, 0)
        conn.close()
    except sqlite3.Error:
        return result

    sales_rows = int(sales_row[0] or 0)
    units_sold = int(sales_row[1] or 0)
    returns = int(sales_row[2] or 0)
    sales_revenue = safe_float(sales_row[3])
    order_rows = int(orders_row[0] or 0)
    distinct_orders = int(orders_row[1] or 0)
    cancelled_orders = int(orders_row[2] or 0)
    orders = distinct_orders or max(order_rows - cancelled_orders, 0)
    orders_revenue = safe_float(orders_row[3])

    return {
        "sales_rows": sales_rows,
        "units_sold": units_sold,
        "returns": returns,
        "sales_revenue": sales_revenue,
        "order_rows": order_rows,
        "orders": orders,
        "cancelled_orders": cancelled_orders,
        "orders_revenue": orders_revenue,
        "available": bool(sales_rows or order_rows),
    }


def _build_business_period(user_id: int, start_date: str, end_date: str, context: Any) -> dict[str, Any]:
    business_metrics = telegram_bot._business_metrics_snapshot(user_id, start_date, end_date, context=context)
    management = telegram_bot._report_mgmt_snapshot(user_id, (start_date, end_date), context=context)
    sqlite_metrics = _sqlite_business_aggregate(user_id, start_date, end_date)

    revenue = _first_number(
        management.get("revenue"),
        business_metrics.get("operational_revenue"),
        sqlite_metrics.get("sales_revenue"),
        sqlite_metrics.get("orders_revenue"),
    )
    profit = _first_number(
        management.get("recommended_profit"),
        management.get("management_profit_with_storage"),
        management.get("management_profit"),
        business_metrics.get("operational_net_profit"),
        business_metrics.get("official_net_profit"),
        business_metrics.get("legacy_financial_profit_estimate"),
    )
    orders = safe_int(sqlite_metrics.get("orders"), 0)
    returns = safe_int(sqlite_metrics.get("returns"), 0)
    units_sold = safe_int(sqlite_metrics.get("units_sold"), 0)
    average_order_value = round(revenue / orders, 2) if revenue is not None and orders > 0 else None
    margin = _first_number(
        management.get("management_margin"),
        ((profit / revenue) * 100) if revenue not in (None, 0) and profit is not None else None,
    )
    has_sqlite_rows = bool(sqlite_metrics.get("available"))
    looks_empty = (
        not has_sqlite_rows
        and revenue in (None, 0, 0.0)
        and profit in (None, 0, 0.0)
        and orders == 0
        and returns == 0
        and units_sold == 0
    )

    if looks_empty:
        revenue = None
        profit = None
        margin = None
        orders = 0
        returns = 0
        average_order_value = None
        units_sold = 0

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": margin,
        "orders": orders,
        "returns": returns,
        "averageOrderValue": average_order_value,
        "unitsSold": units_sold,
        "available": not looks_empty,
    }


def _trend_delta(current_value: float | None, previous_value: float | None) -> float:
    if current_value is None or previous_value is None:
        return 0.0
    if previous_value == 0:
        return 100.0 if current_value > 0 else 0.0
    return round(((current_value - previous_value) / abs(previous_value)) * 100, 1)


def get_business_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    director = telegram_bot._director_snapshot(user_id, (start_date, end_date), context=context)
    sku_rows, _ = telegram_bot._sku_analytics_rows(user_id, (start_date, end_date))
    summary = _build_business_period(user_id, start_date, end_date, context)
    today_start, today_end = _days_window(1)
    yesterday_start = (datetime.now().date() - timedelta(days=1)).isoformat()
    yesterday = _build_business_period(user_id, yesterday_start, yesterday_start, context)
    today = _build_business_period(user_id, today_start, today_end, context)
    seven_days = _build_business_period(user_id, *_days_window(7), context)
    thirty_days = summary

    revenue = summary.get("revenue")
    profit = summary.get("profit")
    margin = summary.get("margin")
    health_score = {
        "GOOD": 84,
        "NORMAL": 72,
        "WARNING": 58,
        "CRITICAL": 32,
    }.get(str(director.get("business_health") or "UNKNOWN").upper(), 50)

    top_products = []
    for row in sorted(sku_rows, key=lambda item: float(item.get("revenue") or 0), reverse=True)[:3]:
        top_products.append(
            {
                "sku": safe_text(row.get("article"), "unknown"),
                "title": safe_text(row.get("article"), "unknown"),
                "revenue": safe_float(row.get("revenue"), 0.0) or 0.0,
                "profit": safe_float(row.get("contribution_profit"), 0.0) or 0.0,
                "margin": safe_float(row.get("real_margin"), 0.0) or 0.0,
                "status": safe_text((row.get("verdicts") or ["Stable"])[0], "Stable"),
            }
        )

    has_business_data = bool(summary.get("available") or top_products)
    health_status = safe_text(director.get("business_health"), "Unknown") if has_business_data else NO_BUSINESS_DATA_STATUS

    return {
        "summary": {
            "revenue": revenue,
            "profit": profit,
            "margin": margin,
            "orders": summary.get("orders") if has_business_data else None,
            "returns": summary.get("returns") if has_business_data else None,
            "averageOrderValue": summary.get("averageOrderValue") if has_business_data else None,
            "unitsSold": summary.get("unitsSold") if has_business_data else None,
        },
        "trends": {
            "revenue": _trend_delta(today.get("revenue"), yesterday.get("revenue")),
            "profit": _trend_delta(today.get("profit"), yesterday.get("profit")),
            "margin": round((today.get("margin") or 0) - (yesterday.get("margin") or 0), 1),
            "returns": _trend_delta(today.get("returns"), yesterday.get("returns")),
        },
        "healthScore": health_score if has_business_data else 0,
        "healthStatus": health_status,
        "periods": {
            "today": {"key": "today", "label": "Today", **today},
            "yesterday": {"key": "yesterday", "label": "Yesterday", **yesterday},
            "sevenDays": {"key": "sevenDays", "label": "7 Days", **seven_days},
            "thirtyDays": {"key": "thirtyDays", "label": "30 Days", **thirty_days},
        },
        "topProducts": top_products,
        "generatedAt": end_date,
    }
