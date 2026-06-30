from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import DEFAULT_USER_ID, current_month_days, route_for_workspace, safe_float, safe_int, safe_text, snapshot_context, status_to_severity, status_to_tone


def get_business_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    business_metrics = telegram_bot._business_metrics_snapshot(user_id, start_date, end_date, context=context)
    director = telegram_bot._director_snapshot(user_id, (start_date, end_date), context=context)
    sku_rows, _ = telegram_bot._sku_analytics_rows(user_id, (start_date, end_date))

    revenue = safe_float(business_metrics.get("operational_revenue"), 0.0) or 0.0
    profit = safe_float(
        business_metrics.get("operational_net_profit")
        or business_metrics.get("official_net_profit")
        or business_metrics.get("legacy_financial_profit_estimate"),
        0.0,
    ) or 0.0
    margin = round((profit / revenue) * 100, 1) if revenue else 0.0
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

    return {
        "summary": {
            "revenue": revenue,
            "profit": profit,
            "margin": margin,
            "orders": 0,
            "returns": 0,
            "averageOrderValue": 0,
            "unitsSold": sum(int(row.get("sales") or 0) for row in sku_rows),
        },
        "trends": {
            "revenue": 0,
            "profit": 0,
            "margin": 0,
            "returns": 0,
        },
        "healthScore": health_score,
        "healthStatus": safe_text(director.get("business_health"), "Unknown"),
        "periods": {
            "today": {"key": "today", "label": "Today", "revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
            "yesterday": {"key": "yesterday", "label": "Yesterday", "revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
            "sevenDays": {"key": "sevenDays", "label": "7 Days", "revenue": revenue, "profit": profit, "margin": margin, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": sum(int(row.get("sales") or 0) for row in sku_rows)},
            "thirtyDays": {"key": "thirtyDays", "label": "30 Days", "revenue": revenue, "profit": profit, "margin": margin, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": sum(int(row.get("sales") or 0) for row in sku_rows)},
        },
        "topProducts": top_products,
        "generatedAt": business_metrics.get("period_end") or end_date,
    }

