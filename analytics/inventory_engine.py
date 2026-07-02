from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

import telegram_bot

from analytics.common import current_month_days, safe_float, safe_text
from config import DB_NAME
from db_manager import init_db
from report import get_replenishment_plan, get_replenishment_settings, get_stock_forecast


RISK_LABELS = {
    "OUT_OF_STOCK": "Нет остатков",
    "CRITICAL_LOW": "Критически низкий запас",
    "LOW": "Низкий запас",
    "NORMAL": "Нормальный запас",
    "OVERSTOCK": "Избыточный запас",
    "UNKNOWN": "Недостаточно данных",
}

RECOMMENDATION_LABELS = {
    "RESTOCK_NOW": "Срочно пополнить",
    "RESTOCK_SOON": "Запланировать пополнение",
    "KEEP_WATCH": "Держать под контролем",
    "SCALE_ALLOWED": "Можно масштабировать",
    "DO_NOT_SCALE": "Не масштабировать до уточнения",
    "REDUCE_ADS_UNTIL_RESTOCK": "Снизить рекламу до пополнения",
    "CLEAR_OVERSTOCK": "Сократить избыточный запас",
    "WAIT_FOR_DATA": "Дождаться данных",
}

RISK_TONE = {
    "OUT_OF_STOCK": "risk",
    "CRITICAL_LOW": "risk",
    "LOW": "watch",
    "NORMAL": "healthy",
    "OVERSTOCK": "accent",
    "UNKNOWN": "neutral",
}

RISK_SEVERITY = {
    "OUT_OF_STOCK": "critical",
    "CRITICAL_LOW": "critical",
    "LOW": "high",
    "NORMAL": "low",
    "OVERSTOCK": "medium",
    "UNKNOWN": "info",
}

RECOMMENDATION_PRIORITY = {
    "RESTOCK_NOW": "critical",
    "REDUCE_ADS_UNTIL_RESTOCK": "critical",
    "RESTOCK_SOON": "high",
    "DO_NOT_SCALE": "high",
    "KEEP_WATCH": "medium",
    "CLEAR_OVERSTOCK": "medium",
    "SCALE_ALLOWED": "low",
    "WAIT_FOR_DATA": "info",
}


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _to_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else text


def _fetch_latest_stock_rows(user_id: int) -> tuple[str | None, list[sqlite3.Row]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(stock_date) FROM stocks WHERE telegram_id=?", (user_id,))
        snapshot_date = _to_iso_date(cur.fetchone()[0])
        if not snapshot_date:
            return None, []
        cur.execute(
            """
            SELECT
                supplier_article,
                nm_id,
                barcode,
                warehouse_name,
                COALESCE(quantity, 0) AS quantity,
                COALESCE(quantity_full, 0) AS quantity_full,
                COALESCE(in_way_to_client, 0) AS in_way_to_client,
                COALESCE(in_way_from_client, 0) AS in_way_from_client
            FROM stocks
            WHERE telegram_id=? AND substr(stock_date, 1, 10)=?
            ORDER BY supplier_article, warehouse_name
            """,
            (user_id, snapshot_date),
        )
        return snapshot_date, cur.fetchall()
    finally:
        conn.close()


def _fetch_sales_aggregate_by_article(user_id: int, start_date: str, end_date: str) -> dict[str, dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                supplier_article,
                COUNT(*) AS orders_count,
                COALESCE(SUM(for_pay), 0) AS revenue,
                MAX(nm_id) AS nm_id,
                MAX(barcode) AS barcode,
                MAX(warehouse_name) AS warehouse_name
            FROM sales
            WHERE telegram_id=?
              AND substr(sale_date, 1, 10) BETWEEN ? AND ?
              AND COALESCE(is_return, 0)=0
            GROUP BY supplier_article
            """,
            (user_id, start_date, end_date),
        )
        result: dict[str, dict[str, Any]] = {}
        for row in cur.fetchall():
            article = safe_text(row["supplier_article"], "").strip()
            if not article:
                continue
            result[article] = {
                "orders": int(row["orders_count"] or 0),
                "revenue": safe_float(row["revenue"]),
                "nm_id": row["nm_id"],
                "barcode": row["barcode"],
                "warehouse_name": safe_text(row["warehouse_name"], "Нет данных"),
            }
        return result
    finally:
        conn.close()


def _fetch_ads_by_article(user_id: int, days: int = 30) -> dict[str, dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                supplier_article,
                COALESCE(SUM(spend), 0) AS spend,
                COALESCE(SUM(sum_price), 0) AS revenue
            FROM advertising
            WHERE telegram_id=?
              AND substr(advert_date, 1, 10) >= date('now', ?)
            GROUP BY supplier_article
            """,
            (user_id, f"-{max(1, int(days)) - 1} day"),
        )
        return {
            safe_text(row["supplier_article"], ""): {
                "spend": safe_float(row["spend"]),
                "adsRevenue": safe_float(row["revenue"]),
            }
            for row in cur.fetchall()
            if safe_text(row["supplier_article"], "")
        }
    finally:
        conn.close()


def _fetch_stock_history(user_id: int, since_days: int | None = None) -> tuple[str | None, int | None]:
    conn = _connect()
    try:
        cur = conn.cursor()
        query = """
            SELECT substr(stock_date, 1, 10) AS snapshot_date, COALESCE(SUM(quantity), 0) AS total_stock
            FROM stocks
            WHERE telegram_id=?
        """
        params: list[Any] = [user_id]
        if since_days is not None:
            query += " AND substr(stock_date, 1, 10) >= date('now', ?)"
            params.append(f"-{max(1, int(since_days)) - 1} day")
        query += " GROUP BY substr(stock_date, 1, 10) ORDER BY snapshot_date DESC LIMIT 1"
        cur.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None, None
        return _to_iso_date(row["snapshot_date"]), int(row["total_stock"] or 0)
    finally:
        conn.close()


def _sku_name_registry(user_id: int, period: tuple[str, str]) -> dict[str, str]:
    names: dict[str, str] = {}
    try:
        snapshot = telegram_bot._sku_registry_snapshot(user_id, period)
        for row in list(snapshot.get("items") or []):
            article = safe_text(row.get("article") or row.get("supplier_article"), "").strip()
            title = safe_text(row.get("name") or row.get("title") or article, article).strip()
            if article and title:
                names[article] = title
    except Exception:
        pass
    try:
        rows, _ = telegram_bot._sku_analytics_rows(user_id, period)
        for row in list(rows or []):
            article = safe_text(row.get("article") or row.get("supplier_article"), "").strip()
            title = safe_text(row.get("name") or row.get("title") or article, article).strip()
            if article and title and article not in names:
                names[article] = title
    except Exception:
        pass
    return names


def _action_plan_by_article(user_id: int, period: tuple[str, str]) -> dict[str, dict[str, Any]]:
    actions: dict[str, dict[str, Any]] = {}
    try:
        actionplan = telegram_bot._sku_actionplan_snapshot(user_id, period)
    except Exception:
        return actions
    for group_name, rows in dict(actionplan.get("groups") or {}).items():
        for row in list(rows or []):
            article = safe_text(row.get("article") or row.get("supplier_article"), "").strip()
            if not article:
                continue
            actions[article] = {
                "group": safe_text(group_name, "WATCH"),
                "action": safe_text(row.get("action"), "WATCH"),
                "next_step": safe_text(row.get("next_step"), ""),
                "reasons": [safe_text(reason, "") for reason in list(row.get("reasons") or []) if safe_text(reason, "")],
            }
    return actions


def _risk_code(stock: int | None, coverage_days: float | None, settings: dict[str, Any]) -> str:
    if stock is None:
        return "UNKNOWN"
    if stock <= 0:
        return "OUT_OF_STOCK"
    if coverage_days is None:
        return "UNKNOWN"
    safety_days = int(settings.get("safety_stock_days") or 0)
    lead_days = int(settings.get("lead_time_days") or 0)
    target_days = int(settings.get("target_stock_days") or 0)
    if coverage_days <= max(1, safety_days):
        return "CRITICAL_LOW"
    if coverage_days <= max(1, safety_days + lead_days):
        return "LOW"
    if target_days > 0 and coverage_days >= (target_days + lead_days + safety_days) * 1.5:
        return "OVERSTOCK"
    return "NORMAL"


def _recommendation_code(
    *,
    risk_code: str,
    stock: int | None,
    coverage_days: float | None,
    ads_spend: float | None,
    sales_velocity: float | None,
    settings: dict[str, Any],
) -> str:
    if stock is None or (coverage_days is None and not sales_velocity):
        return "WAIT_FOR_DATA"
    if risk_code in {"OUT_OF_STOCK", "CRITICAL_LOW"}:
        return "REDUCE_ADS_UNTIL_RESTOCK" if (ads_spend or 0) > 0 else "RESTOCK_NOW"
    if risk_code == "LOW":
        return "RESTOCK_SOON"
    if risk_code == "OVERSTOCK":
        return "CLEAR_OVERSTOCK"
    if (
        risk_code == "NORMAL"
        and coverage_days is not None
        and coverage_days >= (int(settings.get("lead_time_days") or 0) + int(settings.get("safety_stock_days") or 0) + 7)
        and (sales_velocity or 0) > 0
    ):
        return "SCALE_ALLOWED"
    return "KEEP_WATCH"


def build_inventory_analysis(user_id: int) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    period = (start_date, end_date)
    settings = get_replenishment_settings(user_id)
    snapshot_date, stock_rows = _fetch_latest_stock_rows(user_id)
    forecast_rows = {
        safe_text(row.get("article"), ""): row
        for row in get_stock_forecast(
            user_id,
            int(settings.get("target_stock_days") or 45) + int(settings.get("lead_time_days") or 14) + int(settings.get("safety_stock_days") or 7),
            int(settings.get("sales_window_days") or 30),
        )
        if safe_text(row.get("article"), "")
    }
    replenishment_plan = get_replenishment_plan(user_id)
    sales_now = _fetch_sales_aggregate_by_article(user_id, start_date, end_date)
    ads_30 = _fetch_ads_by_article(user_id, 30)
    names = _sku_name_registry(user_id, period)
    action_plan = _action_plan_by_article(user_id, period)

    stock_by_article: dict[str, dict[str, Any]] = {}
    warehouse_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "id": "",
            "warehouse": "",
            "currentStock": 0,
            "criticalSku": 0,
            "forecast": "Ожидание аналитики",
            "health": "Нет данных",
            "status": "Нет данных по складу",
        }
    )
    sku_warehouses: dict[str, list[str]] = defaultdict(list)
    sku_primary_warehouse: dict[str, str] = {}

    for row in stock_rows:
        article = safe_text(row["supplier_article"], "").strip()
        if not article:
            continue
        stock_entry = stock_by_article.setdefault(
            article,
            {
                "stock": 0,
                "quantity_full": 0,
                "reserved": 0,
                "available": 0,
                "nmId": row["nm_id"],
                "barcode": row["barcode"],
            },
        )
        quantity = int(row["quantity"] or 0)
        quantity_full = int(row["quantity_full"] or 0)
        in_way_to_client = int(row["in_way_to_client"] or 0)
        in_way_from_client = int(row["in_way_from_client"] or 0)
        warehouse = safe_text(row["warehouse_name"], "Без склада")

        stock_entry["stock"] += quantity
        stock_entry["quantity_full"] += quantity_full
        stock_entry["reserved"] += max(0, quantity_full - quantity)
        stock_entry["available"] += max(0, quantity + in_way_from_client)
        stock_entry["nmId"] = stock_entry["nmId"] or row["nm_id"]
        stock_entry["barcode"] = stock_entry["barcode"] or row["barcode"]

        sku_warehouses[article].append(warehouse)
        sku_primary_warehouse.setdefault(article, warehouse)

        entry = warehouse_totals[warehouse]
        entry["id"] = f"warehouse-{warehouse.lower().replace(' ', '-')}"
        entry["warehouse"] = warehouse
        entry["currentStock"] += quantity

    sku_keys = sorted(set(stock_by_article) | set(forecast_rows) | set(sales_now) | set(action_plan))
    items: list[dict[str, Any]] = []
    critical_count = 0
    low_count = 0
    overstock_count = 0
    out_of_stock_count = 0
    in_stock_count = 0
    coverage_values: list[float] = []
    scale_allowed_count = 0
    alerts: list[dict[str, Any]] = []

    for sku in sku_keys:
        forecast = dict(forecast_rows.get(sku) or {})
        stock_data = dict(stock_by_article.get(sku) or {})
        sales_data = dict(sales_now.get(sku) or {})
        ads_data = dict(ads_30.get(sku) or {})
        action_data = dict(action_plan.get(sku) or {})

        stock = stock_data.get("stock")
        reserved = stock_data.get("reserved")
        available = stock_data.get("available")
        sales_velocity = safe_float(forecast.get("avg_sales_per_day"))
        coverage_days = safe_float(forecast.get("days_left"))
        risk_code = _risk_code(stock, coverage_days, settings)
        recommendation_code = _recommendation_code(
            risk_code=risk_code,
            stock=stock,
            coverage_days=coverage_days,
            ads_spend=safe_float(ads_data.get("spend")),
            sales_velocity=sales_velocity,
            settings=settings,
        )
        priority = RECOMMENDATION_PRIORITY[recommendation_code]
        tone = RISK_TONE[risk_code]
        recommendation_text = action_data.get("next_step") or RECOMMENDATION_LABELS[recommendation_code]
        reasons = list(action_data.get("reasons") or [])
        linked_revenue = safe_float(sales_data.get("revenue"))
        linked_ad_spend = safe_float(ads_data.get("spend"))
        name = names.get(sku) or safe_text(sku, "SKU")
        warehouse = ", ".join(sorted(set(sku_warehouses.get(sku) or []))) or safe_text(
            sales_data.get("warehouse_name"), "Нет данных"
        )
        scale_allowed = recommendation_code == "SCALE_ALLOWED"

        if stock is not None and stock > 0:
            in_stock_count += 1
        if risk_code in {"OUT_OF_STOCK", "CRITICAL_LOW"}:
            critical_count += 1
        if risk_code == "LOW":
            low_count += 1
        if risk_code == "OVERSTOCK":
            overstock_count += 1
        if risk_code == "OUT_OF_STOCK":
            out_of_stock_count += 1
        if scale_allowed:
            scale_allowed_count += 1
        if coverage_days is not None:
            coverage_values.append(float(coverage_days))

        item = {
            "sku": sku,
            "nmId": stock_data.get("nmId") or sales_data.get("nm_id"),
            "barcode": stock_data.get("barcode") or sales_data.get("barcode"),
            "name": name,
            "stock": stock,
            "reserved": reserved,
            "available": available,
            "daysLeft": coverage_days,
            "coverageDays": coverage_days,
            "salesVelocity": sales_velocity,
            "forecast": (
                f"Продаж в день: {sales_velocity}"
                if sales_velocity is not None
                else "Показатель появится после загрузки продаж"
            ),
            "warehouse": warehouse,
            "health": RISK_LABELS[risk_code],
            "risk": RISK_LABELS[risk_code],
            "riskCode": risk_code,
            "priority": recommendation_code.replace("_", " "),
            "recommendation": recommendation_text,
            "recommendationCode": recommendation_code,
            "linkedRevenue": linked_revenue,
            "linkedAdvertisingSpend": linked_ad_spend,
            "scaleAllowed": scale_allowed,
            "status": {
                "label": RISK_LABELS[risk_code],
                "tone": tone,
            },
            "signals": reasons,
        }
        items.append(item)

        if risk_code in {"OUT_OF_STOCK", "CRITICAL_LOW", "LOW"}:
            alerts.append(
                {
                    "id": f"inventory-alert-{sku.lower()}",
                    "title": f"{name}: {RISK_LABELS[risk_code]}",
                    "description": recommendation_text,
                    "severity": RISK_SEVERITY[risk_code],
                    "source": "backend",
                }
            )

    items.sort(
        key=lambda item: (
            {"OUT_OF_STOCK": 0, "CRITICAL_LOW": 1, "LOW": 2, "NORMAL": 3, "OVERSTOCK": 4, "UNKNOWN": 5}.get(
                safe_text(item.get("riskCode"), "UNKNOWN"),
                9,
            ),
            999999 if item.get("coverageDays") is None else float(item["coverageDays"]),
            safe_text(item.get("sku"), ""),
        )
    )

    for item in items:
        for warehouse in sku_warehouses.get(item["sku"], []):
            if item["riskCode"] in {"OUT_OF_STOCK", "CRITICAL_LOW", "LOW"}:
                warehouse_totals[warehouse]["criticalSku"] += 1

    for entry in warehouse_totals.values():
        critical_sku = int(entry["criticalSku"] or 0)
        if critical_sku >= 3:
            entry["health"] = "Под давлением"
            entry["forecast"] = "Нужно ускорить пополнение"
            entry["status"] = "Есть несколько SKU с риском дефицита."
        elif critical_sku > 0:
            entry["health"] = "Требует внимания"
            entry["forecast"] = "Следить за оборачиваемостью"
            entry["status"] = "Есть SKU с низким запасом."
        else:
            entry["health"] = "Стабильно"
            entry["forecast"] = "План поставок в норме"
            entry["status"] = "Критичных сигналов по складу нет."

    restock_plan: list[dict[str, Any]] = []
    for index, row in enumerate(list(replenishment_plan.get("items") or [])[:8], 1):
        sku = safe_text(row.get("article"), "")
        expected_coverage = safe_float(row.get("target_stock_days"))
        restock_plan.append(
            {
                "id": f"restock-{index}",
                "sku": sku,
                "recommendedQuantity": int(row.get("need") or 0),
                "priority": "critical" if safe_text(row.get("risk_level")) in {"no_stock", "critical"} else "high",
                "reason": RECOMMENDATION_LABELS["RESTOCK_NOW"]
                if safe_text(row.get("risk_level")) in {"no_stock", "critical"}
                else RECOMMENDATION_LABELS["RESTOCK_SOON"],
                "expectedCoverage": (
                    f"{int(expected_coverage)} дней" if expected_coverage is not None else "Нет данных"
                ),
                "warehouse": safe_text(sku_primary_warehouse.get(sku), "Нет данных"),
            }
        )

    supply_priority = [
        {
            "id": f"supply-{index}",
            "level": item["status"]["tone"] == "risk" and "critical" or ("high" if item["status"]["tone"] == "watch" else "medium"),
            "reason": item["risk"],
            "recommendation": item["recommendation"],
        }
        for index, item in enumerate(items[:6], 1)
    ]

    has_real_stock = bool(stock_rows)
    total_stock = sum(int(item.get("stock") or 0) for item in items if item.get("stock") is not None)
    total_sku = len(items)
    forecast_coverage = None
    if total_sku and coverage_values:
        forecast_coverage = round(
            (sum(1 for value in coverage_values if value >= max(1, int(settings.get("safety_stock_days") or 0))) / total_sku) * 100,
            1,
        )
    inventory_health = (
        "DEGRADED"
        if not items or not has_real_stock
        else "CRITICAL"
        if critical_count > 0
        else "WARNING"
        if low_count > 0
        else "GOOD"
    )
    days_left_average = round(sum(coverage_values) / len(coverage_values), 1) if coverage_values else None
    last_updated = snapshot_date or end_date
    warehouse_status = (
        "Нет данных по складам. Данные появятся после первой синхронизации."
        if not warehouse_totals
        else f"В контуре {len(warehouse_totals)} склад(ов); критичных SKU: {critical_count}, низкий запас: {low_count}."
    )

    history = []
    for period_key, period_days, label in (
        ("today", 1, "Текущий срез по остаткам."),
        ("sevenDays", 7, "Последний доступный срез за 7 дней."),
        ("thirtyDays", 30, "Последний доступный срез за 30 дней."),
        ("ninetyDays", 90, "Последний доступный срез за 90 дней."),
    ):
        history_date, history_stock = _fetch_stock_history(user_id, since_days=period_days)
        history.append(
            {
                "period": period_key,
                "stock": history_stock,
                "coverage": forecast_coverage if history_stock is not None else None,
                "note": label if history_date else "Нет исторического среза по остаткам.",
            }
        )

    metrics = [
        {
            "label": "Статус остатков",
            "value": "Нет данных" if not items else RISK_LABELS.get(items[0]["riskCode"], "Нет данных"),
            "note": "Оценка строится по покрытию запаса, продажам и последнему складу WB.",
            "tone": RISK_TONE.get(items[0]["riskCode"], "neutral") if items else "neutral",
        },
        {
            "label": "Покрытие прогноза",
            "value": f"{forecast_coverage:.0f}%" if forecast_coverage is not None else "Нет данных",
            "note": "Доля SKU, для которых запас перекрывает минимальный безопасный горизонт.",
            "tone": "accent" if forecast_coverage is not None else "neutral",
        },
        {
            "label": "Средний запас, дней",
            "value": str(days_left_average) if days_left_average is not None else "Нет данных",
            "note": "Среднее покрытие по SKU, где доступны остаток и скорость продаж.",
            "tone": "watch" if days_left_average is not None else "neutral",
        },
        {
            "label": "SKU готовы к масштабу",
            "value": str(scale_allowed_count),
            "note": "SKU с устойчивым запасом и подтвержденной скоростью продаж.",
            "tone": "healthy" if scale_allowed_count else "neutral",
        },
    ]

    timeline = [
        {
            "id": "inventory-timeline-stock-sync",
            "title": "Срез остатков обновлен",
            "description": f"Последний складской снимок: {snapshot_date}." if snapshot_date else "Складские данные еще не загружены.",
            "period": "sync",
            "severity": "low" if snapshot_date else "info",
            "source": "backend",
        },
        {
            "id": "inventory-timeline-forecast",
            "title": "Прогноз покрытия пересчитан",
            "description": "Покрытие считается по средним продажам и настройкам пополнения.",
            "period": "forecast",
            "severity": "low",
            "source": "backend",
        },
    ]
    if restock_plan:
        timeline.append(
            {
                "id": "inventory-timeline-restock",
                "title": "План пополнения сформирован",
                "description": f"В план включено {len(restock_plan)} SKU с реальной рекомендацией по пополнению.",
                "period": "restock",
                "severity": "medium" if critical_count else "low",
                "source": "backend",
            }
        )

    return {
        "summary": {
            "totalStock": total_stock if has_real_stock else None,
            "criticalSku": critical_count if has_real_stock else None,
            "daysLeftAverage": days_left_average,
            "forecastCoverage": forecast_coverage,
            "inventoryHealth": inventory_health,
            "warehouseCount": len(warehouse_totals) if warehouse_totals else None,
            "lastUpdated": last_updated,
            "totalSku": total_sku,
            "inStockSku": in_stock_count if has_real_stock else None,
            "outOfStockSku": out_of_stock_count if has_real_stock else None,
            "lowStockSku": low_count if has_real_stock else None,
            "overstockSku": overstock_count if has_real_stock else None,
            "estimatedCoverageDays": days_left_average,
            "status": "Данные появятся после первой синхронизации" if not has_real_stock else warehouse_status,
        },
        "health": {
            "inventoryHealth": inventory_health,
            "coverage": forecast_coverage,
            "forecastConfidence": "Высокая" if coverage_values else "Нет данных",
            "criticalStock": critical_count if has_real_stock else None,
            "lowStock": low_count if has_real_stock else None,
            "warehouseStatus": warehouse_status,
        },
        "items": items,
        "restockPlan": restock_plan,
        "supplyPriority": supply_priority,
        "warehouses": list(warehouse_totals.values()),
        "history": history,
        "alerts": alerts[:8]
        if alerts
        else [
            {
                "id": "inventory-alert-empty",
                "title": "Нет складских данных",
                "description": "Данные появятся после первой синхронизации остатков Wildberries.",
                "severity": "info",
                "source": "backend",
            }
        ],
        "timeline": timeline,
        "metrics": metrics,
        "lastUpdated": last_updated,
        "settings": settings,
        "runtimeSource": "live" if has_real_stock else "degraded",
    }
