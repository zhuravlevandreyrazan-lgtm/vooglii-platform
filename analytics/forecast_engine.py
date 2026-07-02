from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from analytics.advertising import get_advertising_payload
from analytics.business import get_business_payload, normalize_business_payload
from analytics.common import DEFAULT_USER_ID, now_iso, safe_float, safe_int, safe_text
from analytics.finance import get_finance_payload
from analytics.inventory import get_inventory_payload
from analytics.products import get_products_payload
from config import DB_NAME
from db_manager import init_db


FORECAST_WINDOWS = {
    "sevenDays": 7,
    "fourteenDays": 14,
    "thirtyDays": 30,
}

MIN_READY_DAYS = 7
MIN_PARTIAL_DAYS = 3


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _date_days_ago(days: int) -> str:
    return (datetime.now().date() - timedelta(days=max(0, days))).isoformat()


def _safe_round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _normalize_status_from_points(non_zero_days: int, total_days: int) -> tuple[str, int | None]:
    if total_days < MIN_PARTIAL_DAYS or non_zero_days < MIN_PARTIAL_DAYS:
        return "insufficient_data", None
    confidence = min(95, max(45, int(round((non_zero_days / max(total_days, 1)) * 100))))
    if total_days < MIN_READY_DAYS or non_zero_days < MIN_READY_DAYS:
        return "degraded", confidence
    return "ready", confidence


def _daily_sales_series(user_id: int, lookback_days: int = 30) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                substr(sale_date, 1, 10) AS day,
                COALESCE(SUM(CASE WHEN COALESCE(is_return, 0)=0 THEN for_pay ELSE 0 END), 0) AS revenue,
                COALESCE(SUM(CASE WHEN COALESCE(is_return, 0)=0 THEN 1 ELSE 0 END), 0) AS units,
                COALESCE(SUM(CASE WHEN COALESCE(is_return, 0)=1 THEN 1 ELSE 0 END), 0) AS returns
            FROM sales
            WHERE telegram_id=?
              AND substr(sale_date, 1, 10) >= ?
            GROUP BY substr(sale_date, 1, 10)
            ORDER BY day
            """,
            (user_id, _date_days_ago(lookback_days - 1)),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _daily_orders_series(user_id: int, lookback_days: int = 30) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                substr(order_date, 1, 10) AS day,
                COUNT(DISTINCT CASE WHEN COALESCE(is_cancel, 0)=0 THEN order_id END) AS orders,
                COALESCE(SUM(CASE WHEN COALESCE(is_cancel, 0)=0 THEN price_with_disc ELSE 0 END), 0) AS revenue
            FROM orders
            WHERE telegram_id=?
              AND substr(order_date, 1, 10) >= ?
            GROUP BY substr(order_date, 1, 10)
            ORDER BY day
            """,
            (user_id, _date_days_ago(lookback_days - 1)),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _daily_ads_series(user_id: int, lookback_days: int = 30) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                substr(advert_date, 1, 10) AS day,
                COALESCE(SUM(spend), 0) AS spend,
                COALESCE(SUM(sum_price), 0) AS revenue
            FROM advertising
            WHERE telegram_id=?
              AND substr(advert_date, 1, 10) >= ?
            GROUP BY substr(advert_date, 1, 10)
            ORDER BY day
            """,
            (user_id, _date_days_ago(lookback_days - 1)),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _trend_label(values: list[float]) -> str:
    if len(values) < 2:
        return "Недостаточно данных"
    pivot = max(1, len(values) // 2)
    first_half = mean(values[:pivot]) if values[:pivot] else 0.0
    second_half = mean(values[pivot:]) if values[pivot:] else 0.0
    if second_half > first_half * 1.08:
        return "Рост"
    if second_half < first_half * 0.92:
        return "Снижение"
    return "Стабильно"


def _window_projection(series: list[dict[str, Any]], horizon_days: int) -> dict[str, Any]:
    daily_revenue = [float(item.get("revenue") or 0.0) for item in series]
    daily_units = [float(item.get("units") or 0.0) for item in series]
    non_zero_days = sum(1 for value in daily_revenue if value > 0)
    status, confidence = _normalize_status_from_points(non_zero_days, len(series))
    if status == "insufficient_data":
        return {
            "status": status,
            "expectedOrders": None,
            "expectedRevenue": None,
            "expectedUnits": None,
            "trend": "Недостаточно данных",
            "confidence": None,
            "explanation": "Для прогноза нужно больше истории продаж и заказов.",
        }

    revenue_per_day = mean(daily_revenue) if daily_revenue else 0.0
    units_per_day = mean(daily_units) if daily_units else 0.0
    recent_tail = daily_revenue[-7:] if len(daily_revenue) >= 7 else daily_revenue
    early_tail = daily_revenue[:7] if len(daily_revenue) >= 7 else daily_revenue
    trend_factor = 1.0
    if recent_tail and early_tail and mean(early_tail) > 0:
        trend_factor = max(0.65, min(1.35, mean(recent_tail) / mean(early_tail)))

    expected_revenue = revenue_per_day * horizon_days * trend_factor
    expected_units = units_per_day * horizon_days * trend_factor
    average_order_value = (mean(daily_revenue) / mean(daily_units)) if mean(daily_units) > 0 else None
    expected_orders = (expected_revenue / average_order_value) if average_order_value not in (None, 0) else expected_units
    return {
        "status": status,
        "expectedOrders": _safe_round(expected_orders, 0),
        "expectedRevenue": _safe_round(expected_revenue),
        "expectedUnits": _safe_round(expected_units, 0),
        "trend": _trend_label(daily_revenue),
        "confidence": confidence,
        "explanation": f"Прогноз построен по {len(series)} дням истории с учетом среднего дневного спроса и текущего тренда.",
    }


def _sales_forecast(user_id: int) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    sales_series = _daily_sales_series(user_id, 30)
    orders_series = _daily_orders_series(user_id, 30)
    orders_by_day = {str(item["day"]): int(item.get("orders") or 0) for item in orders_series}
    combined_series = []
    for item in sales_series:
        combined_series.append(
            {
                "day": item["day"],
                "revenue": float(item.get("revenue") or 0.0),
                "units": float(item.get("units") or 0.0),
                "orders": orders_by_day.get(str(item["day"]), int(item.get("units") or 0)),
            }
        )

    periods = {key: _window_projection(combined_series, days) for key, days in FORECAST_WINDOWS.items()}
    non_zero_days = sum(1 for row in combined_series if float(row.get("revenue") or 0) > 0)
    status, confidence = _normalize_status_from_points(non_zero_days, len(combined_series))
    sales_forecast = {
        "status": status,
        "historyDays": len(combined_series),
        "activeDays": non_zero_days,
        "confidence": confidence,
        "trend": periods["sevenDays"]["trend"],
        "explanation": periods["sevenDays"]["explanation"],
    }
    return periods, sales_forecast, combined_series, orders_series


def _profit_forecast(
    business: dict[str, Any],
    finance: dict[str, Any],
    periods: dict[str, Any],
) -> dict[str, Any]:
    business_summary = dict(business.get("summary") or {})
    finance_summary = dict(finance.get("summary") or {})
    revenue_base = safe_float(business_summary.get("revenue"))
    operating_profit = safe_float(finance_summary.get("operatingProfit"))
    margin = safe_float(business_summary.get("margin"))
    if revenue_base in (None, 0) or operating_profit is None:
        return {
            "status": "insufficient_data",
            "expectedOperatingProfit": None,
            "expectedMargin": None,
            "expectedProfitChange": None,
            "riskOfProfitDrop": None,
            "mainProfitDrivers": [],
            "periods": {key: {"expectedOperatingProfit": None, "expectedMargin": None} for key in FORECAST_WINDOWS},
            "explanation": "Для прогноза прибыли нужно больше данных по выручке и прибыли.",
        }

    margin_ratio = (operating_profit / revenue_base) if revenue_base else None
    if margin is not None:
        margin_ratio = margin / 100.0
    period_rows: dict[str, Any] = {}
    seven_day_profit = None
    for key, period in periods.items():
        expected_revenue = safe_float(period.get("expectedRevenue"))
        expected_profit = expected_revenue * margin_ratio if expected_revenue is not None and margin_ratio is not None else None
        expected_margin = margin if expected_profit is not None else None
        period_rows[key] = {
            "expectedOperatingProfit": _safe_round(expected_profit),
            "expectedMargin": _safe_round(expected_margin),
        }
        if key == "sevenDays":
            seven_day_profit = expected_profit

    risk_of_profit_drop = None
    expected_profit_change = None
    if seven_day_profit is not None and operating_profit is not None and revenue_base:
        observed_days = max(1, datetime.now().day)
        baseline_week_profit = operating_profit / observed_days * 7
        expected_profit_change = _safe_round(seven_day_profit - baseline_week_profit)
        risk_of_profit_drop = bool(expected_profit_change is not None and expected_profit_change < 0)

    drivers = []
    if margin_ratio is not None:
        drivers.append("Историческая маржа бизнеса")
    if safe_float(finance_summary.get("difference")) is not None:
        drivers.append("Разница между управленческой и официальной прибылью")
    if safe_text(finance_summary.get("health"), ""):
        drivers.append("Состояние финансового контура")

    return {
        "status": "ready",
        "expectedOperatingProfit": period_rows["sevenDays"]["expectedOperatingProfit"],
        "expectedMargin": period_rows["sevenDays"]["expectedMargin"],
        "expectedProfitChange": expected_profit_change,
        "riskOfProfitDrop": risk_of_profit_drop,
        "mainProfitDrivers": drivers,
        "periods": period_rows,
        "explanation": "Прогноз прибыли строится из прогноза выручки и текущей управленческой маржи.",
    }


def _inventory_forecast(inventory: dict[str, Any]) -> dict[str, Any]:
    items = list(inventory.get("items") or [])
    summary = dict(inventory.get("summary") or {})
    if not items:
        return {
            "status": "insufficient_data",
            "coverageDays": None,
            "stockoutRisk": None,
            "expectedOutOfStockDate": None,
            "restockNeeded": None,
            "scaleAllowed": None,
            "affectedRevenue": None,
            "message": "Прогноз остатков недоступен до синхронизации склада.",
            "criticalSku": [],
        }

    critical_items = [
        item for item in items if safe_text(item.get("riskCode"), "") in {"OUT_OF_STOCK", "CRITICAL_LOW", "LOW"}
    ]
    first_risk = critical_items[0] if critical_items else None
    oos_date = None
    if first_risk and safe_float(first_risk.get("coverageDays")) is not None:
        oos_date = (datetime.now().date() + timedelta(days=int(float(first_risk["coverageDays"])))).isoformat()
    affected_revenue = sum(float(item.get("linkedRevenue") or 0.0) for item in critical_items) or None
    return {
        "status": "ready",
        "coverageDays": safe_float(summary.get("estimatedCoverageDays")),
        "stockoutRisk": safe_text(first_risk.get("risk"), "Низкий") if first_risk else "Низкий",
        "expectedOutOfStockDate": oos_date,
        "restockNeeded": bool(critical_items),
        "scaleAllowed": any(bool(item.get("scaleAllowed")) for item in items),
        "affectedRevenue": _safe_round(affected_revenue),
        "message": (
            f"SKU {safe_text(first_risk.get('sku'), 'товар')} может закончиться примерно {oos_date}."
            if first_risk and oos_date
            else "Критичных признаков дефицита по остаткам не найдено."
        ),
        "criticalSku": critical_items[:5],
    }


def _advertising_forecast(advertising: dict[str, Any], inventory_forecast: dict[str, Any], ads_series: list[dict[str, Any]]) -> dict[str, Any]:
    summary = dict(advertising.get("summary") or {})
    spend_values = [float(item.get("spend") or 0.0) for item in ads_series]
    revenue_values = [float(item.get("revenue") or 0.0) for item in ads_series]
    non_zero_days = sum(1 for value in spend_values if value > 0)
    status, confidence = _normalize_status_from_points(non_zero_days, len(ads_series))
    if status == "insufficient_data":
        return {
            "status": status,
            "expectedSpend": None,
            "expectedROAS": None,
            "expectedACOS": None,
            "efficiencyTrend": "Недостаточно данных",
            "overspendRisk": None,
            "scalePotential": None,
            "explanation": "Для прогноза рекламы нужно больше истории рекламных расходов.",
        }

    avg_spend = mean(spend_values) if spend_values else 0.0
    avg_revenue = mean(revenue_values) if revenue_values else 0.0
    expected_spend = avg_spend * 7
    expected_roas = (avg_revenue / avg_spend) if avg_spend > 0 else safe_float(summary.get("roas"))
    expected_acos = (avg_spend / avg_revenue * 100) if avg_revenue > 0 else safe_float(summary.get("acos"))
    scale_potential = bool(
        expected_roas is not None
        and expected_roas >= 2.5
        and bool(inventory_forecast.get("scaleAllowed"))
    )
    overspend_risk = bool(expected_acos is not None and expected_acos > 35)
    return {
        "status": status,
        "expectedSpend": _safe_round(expected_spend),
        "expectedROAS": _safe_round(expected_roas),
        "expectedACOS": _safe_round(expected_acos),
        "efficiencyTrend": _trend_label(revenue_values) if revenue_values else "Недостаточно данных",
        "overspendRisk": overspend_risk,
        "scalePotential": scale_potential,
        "confidence": confidence,
        "explanation": "Прогноз рекламы строится по истории расходов и рекламной выручки за последние 30 дней.",
    }


def _build_risks(
    periods: dict[str, Any],
    profit_forecast: dict[str, Any],
    inventory_forecast: dict[str, Any],
    advertising_forecast: dict[str, Any],
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    if profit_forecast.get("riskOfProfitDrop"):
        risks.append(
            {
                "id": "profit-drop",
                "title": "Риск снижения прибыли",
                "description": "Если ничего не менять, прибыль в ближайшие 7 дней может снизиться.",
                "severity": "high",
            }
        )
    if inventory_forecast.get("restockNeeded"):
        risks.append(
            {
                "id": "inventory-stockout",
                "title": "Риск дефицита остатков",
                "description": safe_text(inventory_forecast.get("message"), "Остатки требуют внимания."),
                "severity": "high",
            }
        )
    if advertising_forecast.get("overspendRisk"):
        risks.append(
            {
                "id": "ad-spend-loss",
                "title": "Риск неэффективной рекламы",
                "description": "Рекламные расходы растут быстрее ожидаемой отдачи.",
                "severity": "medium",
            }
        )
    if periods["sevenDays"].get("status") == "degraded":
        risks.append(
            {
                "id": "forecast-confidence",
                "title": "Низкая уверенность прогноза",
                "description": "Истории пока мало, поэтому прогноз нужно трактовать как ранний ориентир.",
                "severity": "medium",
            }
        )
    return risks


def _build_opportunities(inventory_forecast: dict[str, Any], advertising_forecast: dict[str, Any]) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    if advertising_forecast.get("scalePotential"):
        opportunities.append(
            {
                "id": "scale-ads",
                "title": "Можно масштабировать рекламу",
                "description": "Реклама показывает приемлемую эффективность, а по остаткам есть запас для роста.",
                "severity": "low",
            }
        )
    if inventory_forecast.get("scaleAllowed"):
        opportunities.append(
            {
                "id": "inventory-scale",
                "title": "Есть SKU с запасом под рост",
                "description": "Часть SKU можно масштабировать без риска немедленного дефицита.",
                "severity": "low",
            }
        )
    return opportunities


def _scenario_rows(
    periods: dict[str, Any],
    profit_forecast: dict[str, Any],
    risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    revenue_30 = safe_float(periods["thirtyDays"].get("expectedRevenue"))
    profit_30 = safe_float((profit_forecast.get("periods") or {}).get("thirtyDays", {}).get("expectedOperatingProfit"))
    if revenue_30 is None or profit_30 is None:
        return []

    return [
        {
            "id": "conservative",
            "title": "Консервативный сценарий",
            "description": "Сохраняем текущий темп и не масштабируемся до снятия ключевых рисков.",
            "expectedRevenue": _safe_round(revenue_30 * 0.95),
            "expectedProfit": _safe_round(profit_30 * 0.98),
            "riskLevel": "Низкий",
            "actions": ["Не увеличивать рекламу без подтвержденных остатков", "Контролировать дефицит по SKU"],
        },
        {
            "id": "balanced",
            "title": "Оптимальный сценарий",
            "description": "Сохраняем баланс между прибылью, рекламой и остатками.",
            "expectedRevenue": revenue_30,
            "expectedProfit": profit_30,
            "riskLevel": "Средний" if risks else "Низкий",
            "actions": ["Фокус на SKU с подтвержденным запасом", "Масштабировать только эффективную рекламу"],
        },
        {
            "id": "aggressive",
            "title": "Агрессивный сценарий",
            "description": "Ускоряем рост продаж, но усиливаем контроль за остатками и рекламой.",
            "expectedRevenue": _safe_round(revenue_30 * 1.1),
            "expectedProfit": _safe_round(profit_30 * 1.04),
            "riskLevel": "Высокий" if risks else "Средний",
            "actions": ["Увеличить бюджет только по сильным SKU", "Подготовить пополнение заранее"],
        },
    ]


def build_forecast_payload(
    *,
    user_id: int = DEFAULT_USER_ID,
    business: dict[str, Any] | None = None,
    finance: dict[str, Any] | None = None,
    advertising: dict[str, Any] | None = None,
    inventory: dict[str, Any] | None = None,
    products: dict[str, Any] | None = None,
) -> dict[str, Any]:
    business = normalize_business_payload(business or get_business_payload(user_id))
    finance = finance or get_finance_payload(user_id)
    advertising = advertising or get_advertising_payload(user_id)
    inventory = inventory or get_inventory_payload(user_id)
    products = products or get_products_payload(user_id)

    periods, sales_forecast, sales_series, _ = _sales_forecast(user_id)
    ads_series = _daily_ads_series(user_id, 30)
    profit_forecast = _profit_forecast(business, finance, periods)
    inventory_forecast = _inventory_forecast(inventory)
    advertising_forecast = _advertising_forecast(advertising, inventory_forecast, ads_series)
    risks = _build_risks(periods, profit_forecast, inventory_forecast, advertising_forecast)
    opportunities = _build_opportunities(inventory_forecast, advertising_forecast)

    ready_blocks = sum(
        1
        for block in (sales_forecast, profit_forecast, inventory_forecast, advertising_forecast)
        if safe_text(block.get("status"), "").lower() == "ready"
    )
    degraded_blocks = sum(
        1
        for block in (sales_forecast, profit_forecast, inventory_forecast, advertising_forecast)
        if safe_text(block.get("status"), "").lower() == "degraded"
    )

    if ready_blocks == 0 and degraded_blocks == 0:
        summary_status = "insufficient_data"
        confidence = None
        message = "Для прогноза нужно больше истории продаж, рекламы и остатков."
    elif ready_blocks >= 2:
        summary_status = "ready"
        confidences = [block.get("confidence") for block in (sales_forecast, advertising_forecast) if block.get("confidence") is not None]
        confidence = int(round(sum(int(value) for value in confidences) / len(confidences))) if confidences else 72
        message = "Прогноз готов и опирается на историю продаж, рекламы и текущие сигналы по остаткам."
    else:
        summary_status = "degraded"
        confidence = sales_forecast.get("confidence") or advertising_forecast.get("confidence")
        message = "Прогноз собран частично: части данных пока недостаточно для полной уверенности."

    scenarios = _scenario_rows(periods, profit_forecast, risks) if summary_status == "ready" else []
    top_products = list(products.get("products") or [])[:5]

    return {
        "summary": {
            "status": summary_status,
            "message": message,
            "confidence": confidence,
        },
        "periods": periods,
        "salesForecast": sales_forecast,
        "profitForecast": profit_forecast,
        "inventoryForecast": inventory_forecast,
        "advertisingForecast": advertising_forecast,
        "risks": risks,
        "opportunities": opportunities,
        "scenarios": scenarios,
        "supportingProducts": top_products,
        "generatedAt": now_iso(),
    }


def get_forecast_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    return build_forecast_payload(user_id=user_id)


def simulate_forecast_action(
    action_type: str,
    *,
    sku: str | None = None,
    value: float | None = None,
    user_id: int = DEFAULT_USER_ID,
) -> dict[str, Any]:
    forecast = get_forecast_payload(user_id)
    status = safe_text((forecast.get("summary") or {}).get("status"), "insufficient_data")
    if status == "insufficient_data":
        return {
            "status": "insufficient_data",
            "expectedEffect": {},
            "risks": [],
            "recommendation": "Для моделирования нужно больше исходных данных.",
            "confidence": None,
        }

    inventory_forecast = dict(forecast.get("inventoryForecast") or {})
    advertising_forecast = dict(forecast.get("advertisingForecast") or {})
    products = list(forecast.get("supportingProducts") or [])
    selected_product = next((item for item in products if safe_text(item.get("sku"), "") == safe_text(sku, "")), None)
    delta = float(value or 0)

    if action_type == "increase_ads":
        expected_spend = safe_float(advertising_forecast.get("expectedSpend"))
        expected_roas = safe_float(advertising_forecast.get("expectedROAS"))
        if expected_spend is None or expected_roas is None:
            return {
                "status": "insufficient_data",
                "expectedEffect": {},
                "risks": [],
                "recommendation": "Недостаточно рекламной истории для моделирования.",
                "confidence": None,
            }
        spend_delta = expected_spend * (delta / 100.0 if delta else 0.15)
        revenue_delta = spend_delta * expected_roas
        return {
            "status": "ready",
            "expectedEffect": {
                "expectedSpendDelta": _safe_round(spend_delta),
                "expectedRevenueDelta": _safe_round(revenue_delta),
                "selectedSku": safe_text(sku, "all"),
            },
            "risks": [
                "Не увеличивайте рекламу, если по SKU ожидается дефицит."
            ] if inventory_forecast.get("restockNeeded") else [],
            "recommendation": "Увеличивайте бюджет только по SKU с подтвержденным запасом и устойчивым ROAS.",
            "confidence": (forecast.get("summary") or {}).get("confidence"),
        }

    if action_type == "reduce_ads":
        expected_spend = safe_float(advertising_forecast.get("expectedSpend"))
        if expected_spend is None:
            return {
                "status": "insufficient_data",
                "expectedEffect": {},
                "risks": [],
                "recommendation": "Недостаточно рекламной истории для моделирования.",
                "confidence": None,
            }
        spend_delta = expected_spend * (delta / 100.0 if delta else 0.15)
        return {
            "status": "ready",
            "expectedEffect": {
                "expectedSpendDelta": _safe_round(-spend_delta),
                "selectedSku": safe_text(sku, "all"),
            },
            "risks": ["Можно потерять часть выручки, если снизить бюджет по эффективным кампаниям."],
            "recommendation": "Снижайте бюджет по неэффективным связкам, а не по всем кампаниям сразу.",
            "confidence": (forecast.get("summary") or {}).get("confidence"),
        }

    if action_type == "restock":
        if not selected_product and not inventory_forecast.get("restockNeeded"):
            return {
                "status": "insufficient_data",
                "expectedEffect": {},
                "risks": [],
                "recommendation": "Нет подтвержденных SKU для пополнения.",
                "confidence": None,
            }
        return {
            "status": "ready",
            "expectedEffect": {
                "selectedSku": safe_text(sku, "portfolio"),
                "riskReduction": "Снижение риска дефицита остатков",
                "protectedRevenue": inventory_forecast.get("affectedRevenue"),
            },
            "risks": ["Нужно проверить сроки поставки и фактическую доступность товара у поставщика."],
            "recommendation": "Пополнение оправдано, если SKU уже влияет на выручку или рекламу.",
            "confidence": (forecast.get("summary") or {}).get("confidence"),
        }

    return {
        "status": "insufficient_data",
        "expectedEffect": {},
        "risks": [],
        "recommendation": "Этот тип сценария пока не поддерживается.",
        "confidence": None,
    }
