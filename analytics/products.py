from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import DEFAULT_USER_ID, current_month_days, safe_float, safe_int, safe_text, snapshot_context, status_to_severity, status_to_tone


def _product_status(row: dict[str, Any]) -> tuple[str, str]:
    margin = safe_float(row.get("real_margin"), 0.0) or 0.0
    contribution = safe_float(row.get("contribution_profit"), 0.0) or 0.0
    if contribution < 0 or margin < 15:
        return "Restock needed" if margin > 0 else "Margin pressure", "risk" if margin <= 0 else "watch"
    if margin >= 35:
        return "Scaling", "accent"
    return "Stable", "healthy"


def get_products_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    rows, _ = telegram_bot._sku_analytics_rows(user_id, (start_date, end_date))
    actionplan = telegram_bot._sku_actionplan_snapshot(user_id, (start_date, end_date))

    products = []
    for row in rows[:25]:
        status_label, tone = _product_status(row)
        products.append(
            {
                "sku": safe_text(row.get("article"), "unknown"),
                "name": safe_text(row.get("article"), "unknown"),
                "metrics": {
                    "revenue": safe_float(row.get("revenue")),
                    "profit": safe_float(row.get("contribution_profit")),
                    "margin": safe_float(row.get("real_margin")),
                    "roas": None,
                    "acos": None,
                    "stock": None,
                    "daysLeft": None,
                },
                "health": {
                    "health": "Strong" if tone in ("healthy", "accent") else ("Watch" if tone == "watch" else "Risk"),
                    "status": status_label,
                    "abc": "A" if (safe_float(row.get("revenue"), 0.0) or 0) > 10000 else "B",
                    "xyz": "X",
                    "forecast": safe_text((row.get("verdicts") or ["Demand outlook is not available yet"])[0], "Demand outlook is not available yet"),
                    "riskLevel": "Low" if tone in ("healthy", "accent") else ("Medium" if tone == "watch" else "High"),
                },
                "status": {"label": status_label, "tone": tone},
                "recommendation": safe_text((row.get("verdicts") or ["Review economics"])[0], "Review economics"),
                "trend": "Growing" if (safe_float(row.get("revenue"), 0.0) or 0) > 0 else "No product trend available",
                "warehouse": safe_text(row.get("warehouse_name"), "Warehouse data is not connected"),
            }
        )

    recommendations = []
    for action_name, items in dict(actionplan.get("groups") or {}).items():
        for item in list(items or [])[:2]:
            recommendations.append(
                {
                    "id": f"product-rec-{safe_text(item.get('article'))}-{action_name.lower()}",
                    "sku": safe_text(item.get("article"), "unknown"),
                    "recommendation": safe_text(item.get("next_step"), "Review manually"),
                    "reason": "; ".join(list(item.get("reasons") or [])[:3]),
                    "priority": "critical" if action_name == "PAUSE" else ("high" if action_name == "REDUCE" else ("medium" if action_name == "SCALE" else "low")),
                    "confidence": "Medium",
                    "expectedEffect": safe_text(item.get("action"), "Operational review"),
                }
            )

    return {
        "summary": {
            "skuCount": len(products),
            "activeSku": sum(1 for item in products if (item["metrics"]["revenue"] or 0) > 0),
            "problemSku": sum(1 for item in products if item["status"]["tone"] in ("watch", "risk")),
            "riskSku": sum(1 for item in products if item["status"]["tone"] == "risk"),
            "growthSku": sum(1 for item in products if item["status"]["tone"] == "accent"),
            "lastUpdated": end_date,
        },
        "products": products,
        "recommendations": recommendations[:6],
        "history": [],
        "inventoryPreview": products[:5],
        "alerts": [
            {
                "id": "product-alert-1",
                "title": "Product economics require review",
                "description": "At least one SKU has weak margin or negative contribution profit.",
                "severity": "medium",
                "source": "backend",
            }
        ] if any(item["status"]["tone"] in ("watch", "risk") for item in products) else [],
        "timeline": [
            {
                "id": "product-timeline-1",
                "title": "SKU analytics refreshed",
                "description": "Products payload reuses current SKU analytics and action plan builders.",
                "period": "sync",
                "severity": "low",
                "source": "backend",
            }
        ] if products or recommendations else [],
        "actions": [
            {
                "id": f"product-action-{index}",
                "sku": item["sku"],
                "action": item["recommendation"],
                "status": item["status"]["label"],
            }
            for index, item in enumerate(products[:4], 1)
        ],
        "lastUpdated": end_date,
    }
