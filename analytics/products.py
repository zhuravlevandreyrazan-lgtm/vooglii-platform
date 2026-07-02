from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import (
    DEFAULT_USER_ID,
    current_month_days,
    safe_float,
    safe_text,
)
from analytics.inventory_engine import build_inventory_analysis


def _product_status(row: dict[str, Any], inventory_map: dict[str, dict[str, Any]]) -> tuple[str, str]:
    sku = safe_text(row.get("article"), "")
    inventory = inventory_map.get(sku) or {}
    risk_code = safe_text(inventory.get("riskCode"), "")
    if risk_code in {"OUT_OF_STOCK", "CRITICAL_LOW"}:
        return "Нужно пополнение", "risk"
    if risk_code == "LOW":
        return "Низкий запас", "watch"

    margin = safe_float(row.get("real_margin"), 0.0) or 0.0
    contribution = safe_float(row.get("contribution_profit"), 0.0) or 0.0
    if contribution < 0 or margin < 15:
        return "Давление на маржу" if margin <= 0 else "Требует внимания", "watch" if margin > 0 else "risk"
    if margin >= 35 and inventory.get("scaleAllowed"):
        return "Готов к масштабу", "accent"
    return "Стабильно", "healthy"


def get_products_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    rows, _ = telegram_bot._sku_analytics_rows(user_id, (start_date, end_date))
    actionplan = telegram_bot._sku_actionplan_snapshot(user_id, (start_date, end_date))
    inventory_payload = build_inventory_analysis(user_id)
    inventory_map = {
        safe_text(item.get("sku"), ""): item
        for item in list(inventory_payload.get("items") or [])
        if safe_text(item.get("sku"), "")
    }

    products = []
    for row in rows[:25]:
        sku = safe_text(row.get("article"), "unknown")
        inventory = inventory_map.get(sku) or {}
        status_label, tone = _product_status(row, inventory_map)
        verdicts = list(row.get("verdicts") or [])
        products.append(
            {
                "sku": sku,
                "name": safe_text(row.get("name") or row.get("title") or row.get("article"), sku),
                "metrics": {
                    "revenue": safe_float(row.get("revenue")),
                    "profit": safe_float(row.get("contribution_profit")),
                    "margin": safe_float(row.get("real_margin")),
                    "roas": None,
                    "acos": None,
                    "stock": inventory.get("stock"),
                    "daysLeft": inventory.get("coverageDays"),
                },
                "health": {
                    "health": "Стабильно" if tone in ("healthy", "accent") else ("Внимание" if tone == "watch" else "Риск"),
                    "status": status_label,
                    "abc": "A" if (safe_float(row.get("revenue"), 0.0) or 0) > 10000 else "B",
                    "xyz": "X",
                    "forecast": safe_text(
                        (verdicts or [inventory.get("recommendation") or "Прогноз появится после загрузки данных"])[0],
                        "Прогноз появится после загрузки данных",
                    ),
                    "riskLevel": safe_text(inventory.get("risk"), "Нет данных"),
                },
                "status": {"label": status_label, "tone": tone},
                "recommendation": safe_text(
                    inventory.get("recommendation") or (verdicts or ["Проверьте экономику SKU"])[0],
                    "Проверьте экономику SKU",
                ),
                "trend": "Растет" if (safe_float(row.get("revenue"), 0.0) or 0) > 0 else "Недостаточно данных",
                "warehouse": safe_text(inventory.get("warehouse") or row.get("warehouse_name"), "Нет данных"),
                "inventoryRisk": inventory.get("riskCode"),
                "restockRecommendation": inventory.get("recommendationCode"),
                "scaleAllowed": bool(inventory.get("scaleAllowed")),
            }
        )

    recommendations = []
    for action_name, items in dict(actionplan.get("groups") or {}).items():
        for item in list(items or [])[:2]:
            sku = safe_text(item.get("article"), "unknown")
            inventory = inventory_map.get(sku) or {}
            recommendations.append(
                {
                    "id": f"product-rec-{sku}-{action_name.lower()}",
                    "sku": sku,
                    "recommendation": safe_text(
                        inventory.get("recommendation") or item.get("next_step"),
                        "Проверьте SKU вручную",
                    ),
                    "reason": "; ".join(list(item.get("reasons") or [])[:3]) or safe_text(inventory.get("risk"), "Сигнал по SKU"),
                    "priority": "critical"
                    if safe_text(inventory.get("riskCode")) in {"OUT_OF_STOCK", "CRITICAL_LOW"}
                    else ("high" if action_name in {"PAUSE", "REDUCE"} else ("medium" if action_name == "WATCH" else "low")),
                    "confidence": "Высокая" if inventory else "Средняя",
                    "expectedEffect": safe_text(item.get("action"), "Операционная проверка"),
                }
            )

    inventory_preview = []
    for item in list(inventory_payload.get("items") or [])[:5]:
        sku = safe_text(item.get("sku"), "unknown")
        matched = next((product for product in products if product["sku"] == sku), None)
        if matched:
            inventory_preview.append(matched)

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
        "inventoryPreview": inventory_preview,
        "alerts": [
            {
                "id": "product-alert-inventory",
                "title": "Найдены SKU с риском по остаткам",
                "description": "Часть товарной матрицы требует пополнения или ограничения масштаба.",
                "severity": "medium",
                "source": "backend",
            }
        ]
        if any(item["status"]["tone"] in ("watch", "risk") for item in products)
        else [],
        "timeline": [
            {
                "id": "product-timeline-1",
                "title": "SKU-аналитика обновлена",
                "description": "Карточки товаров объединяют продажи, экономику и остатки.",
                "period": "sync",
                "severity": "low",
                "source": "backend",
            }
        ]
        if products or recommendations
        else [],
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
