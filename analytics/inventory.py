from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import DEFAULT_USER_ID, current_month_days, safe_float, safe_text, snapshot_context


def get_inventory_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    sku_registry = telegram_bot._sku_registry_snapshot(user_id, (start_date, end_date), context=snapshot_context())
    actionplan = telegram_bot._sku_actionplan_snapshot(user_id, (start_date, end_date))
    top_priority = list(actionplan.get("top_priority") or [])

    items = [
        {
            "sku": safe_text(item.get("article"), "unknown"),
            "stock": None,
            "reserved": None,
            "available": None,
            "daysLeft": None,
            "forecast": safe_text(item.get("next_step"), "No forecast yet"),
            "warehouse": "n/a",
            "health": "Watch" if item.get("action") in ("REDUCE", "INVESTIGATE") else ("Risk" if item.get("action") == "PAUSE" else "Strong"),
            "priority": safe_text(item.get("action"), "Pending"),
            "recommendation": safe_text(item.get("next_step"), "Review manually"),
            "status": {
                "label": safe_text(item.get("action"), "Pending"),
                "tone": "risk" if item.get("action") == "PAUSE" else ("watch" if item.get("action") in ("REDUCE", "INVESTIGATE") else "healthy"),
            },
        }
        for item in top_priority
    ]

    return {
        "summary": {
            "totalStock": None,
            "criticalSku": sum(1 for item in items if item["status"]["tone"] == "risk"),
            "daysLeftAverage": None,
            "forecastCoverage": safe_float(sku_registry.get("coverage_percent")),
            "inventoryHealth": "WATCH" if any(item["status"]["tone"] in ("watch", "risk") for item in items) else "HEALTHY",
            "warehouseCount": None,
            "lastUpdated": end_date,
        },
        "health": {
            "inventoryHealth": "WATCH" if any(item["status"]["tone"] in ("watch", "risk") for item in items) else "HEALTHY",
            "coverage": safe_float(sku_registry.get("coverage_percent")),
            "forecastConfidence": "Medium",
            "criticalStock": sum(1 for item in items if item["status"]["tone"] == "risk"),
            "lowStock": sum(1 for item in items if item["status"]["tone"] == "watch"),
            "warehouseStatus": "Inventory view currently reuses SKU action plan priorities.",
        },
        "items": items,
        "restockPlan": [
            {
                "id": f"restock-{index}",
                "sku": item["sku"],
                "recommendedQuantity": None,
                "priority": "critical" if item["status"]["tone"] == "risk" else "high",
                "reason": item["recommendation"],
                "expectedCoverage": "n/a",
                "warehouse": item["warehouse"],
            }
            for index, item in enumerate(items[:5], 1)
        ],
        "supplyPriority": [
            {
                "id": f"supply-{index}",
                "level": "critical" if item["status"]["tone"] == "risk" else "high",
                "reason": item["recommendation"],
                "recommendation": item["recommendation"],
            }
            for index, item in enumerate(items[:4], 1)
        ],
        "warehouses": [],
        "history": [
            {"period": "today", "stock": None, "coverage": safe_float(sku_registry.get("coverage_percent")), "note": "Inventory history is not exported yet."},
            {"period": "sevenDays", "stock": None, "coverage": safe_float(sku_registry.get("coverage_percent")), "note": "Inventory history is not exported yet."},
            {"period": "thirtyDays", "stock": None, "coverage": safe_float(sku_registry.get("coverage_percent")), "note": "Inventory history is not exported yet."},
            {"period": "ninetyDays", "stock": None, "coverage": safe_float(sku_registry.get("coverage_percent")), "note": "Inventory history is not exported yet."},
        ],
        "alerts": [
            {
                "id": "inventory-alert-1",
                "title": "Inventory priorities need review",
                "description": "Inventory snapshot currently reflects SKU action plan priorities and registry coverage.",
                "severity": "medium",
                "source": "backend",
            }
        ] if items else [],
        "timeline": [
            {
                "id": "inventory-timeline-1",
                "title": "Inventory priorities refreshed",
                "description": "Inventory payload reuses SKU registry and action plan builders.",
                "period": "sync",
                "severity": "low",
                "source": "backend",
            }
        ],
        "metrics": [
            {"label": "Inventory Health", "value": "WATCH" if items else "UNKNOWN", "note": "Derived from SKU action priorities.", "tone": "watch" if items else "neutral"},
            {"label": "Registry Coverage", "value": f"{safe_float(sku_registry.get('coverage_percent')) or 0}%", "note": "Coverage of SKU cost registry.", "tone": "accent"},
        ],
        "lastUpdated": end_date,
    }

