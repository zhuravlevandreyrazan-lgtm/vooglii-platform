from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.advertising import get_advertising_payload
from analytics.business import get_business_payload, normalize_business_payload
from analytics.cache import get_stale_cache_value
from analytics.common import (
    DEFAULT_USER_ID,
    PRODUCT_NAME,
    current_month_days,
    format_confidence,
    now_iso,
    safe_call,
    safe_float,
    safe_int,
    safe_list,
    safe_text,
    snapshot_context,
    status_to_api,
)
from analytics.decision_engine import get_decision_engine_payload
from analytics.finance import get_finance_payload
from analytics.inventory import get_inventory_payload
from analytics.performance import get_performance_snapshot
from analytics.products import get_products_payload


def _first_number(*values: Any) -> float | None:
    for value in values:
        parsed = safe_float(value)
        if parsed is not None:
            return parsed
    return None


def _format_metric_value(value: float | None, fallback: str = "UNKNOWN") -> str:
    if value is None:
        return fallback
    rounded = round(value, 2)
    if float(rounded).is_integer():
        return str(int(rounded))
    return str(rounded)


def _localize_executive_text(value: Any, fallback: str = "") -> str:
    text = safe_text(value, fallback)
    replacements = {
        "No finance data available": "Финансовые данные пока недоступны.",
        "No advertising data available": "Рекламные данные пока недоступны.",
        "No business data available": "Бизнес-данные пока недоступны.",
        "Difference explanation is not available from backend yet.": "Объяснение финансового расхождения пока недоступно в backend.",
        "Inventory view currently reuses SKU action plan priorities and does not expose live stock counts yet.": "Раздел остатков пока использует SKU-приоритеты и еще не показывает живые складские остатки.",
    }
    return replacements.get(text, text)


def _executive_summary(
    business_summary: dict[str, Any],
    finance_summary: dict[str, Any],
    finance_difference: dict[str, Any],
    advertising_summary: dict[str, Any],
) -> str:
    revenue = _first_number(
        business_summary.get("revenue"),
        finance_difference.get("revenue"),
    )
    profit = _first_number(
        business_summary.get("profit"),
        finance_summary.get("operatingProfit"),
        finance_summary.get("officialProfit"),
    )
    finance_health = safe_text(finance_summary.get("health"), "UNKNOWN")
    ads_health = safe_text(advertising_summary.get("adsHealth"), "UNKNOWN")

    summary_parts = []
    if revenue is not None:
        summary_parts.append(f"Выручка {_format_metric_value(revenue)}")
    if profit is not None:
        summary_parts.append(f"операционная прибыль {_format_metric_value(profit)}")
    if summary_parts:
        headline = " и ".join(summary_parts)
        return f"{headline}. Состояние финансов: {finance_health}; состояние рекламы: {ads_health}."
    return f"Состояние финансов: {finance_health}; состояние рекламы: {ads_health}."


def get_executive_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    return get_executive_payload_fast(user_id)


def _legacy_executive_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    days = (start_date, end_date)
    shared_context = snapshot_context()

    financial_engine_snapshot, financial_engine_error = safe_call(
        "financial_engine_snapshot",
        lambda: telegram_bot._financial_engine_snapshot(start_date, end_date, user=user_id, context=shared_context),
    )
    business_metrics_snapshot, business_metrics_error = safe_call(
        "business_metrics_snapshot",
        lambda: telegram_bot._business_metrics_snapshot(user_id, start_date, end_date, context=shared_context),
    )
    director_snapshot, director_error = safe_call(
        "director_snapshot",
        lambda: telegram_bot._director_snapshot(user_id, days, context=shared_context),
    )
    kpi_snapshot, kpi_error = safe_call(
        "kpi_snapshot",
        lambda: telegram_bot._kpi_snapshot(user_id, days, context=shared_context),
    )
    advisor_snapshot, advisor_error = safe_call(
        "advisor_v2_snapshot",
        lambda: telegram_bot._advisor_v2_snapshot(user_id, days, context=shared_context),
    )
    decision_snapshot, decision_error = safe_call(
        "decision_snapshot",
        lambda: telegram_bot._decision_snapshot(user_id, days, context=shared_context),
    )
    cfo_snapshot, cfo_error = safe_call(
        "cfo_insights_snapshot",
        lambda: telegram_bot._cfo_insights_snapshot(user_id, days, context=shared_context),
    )
    control_snapshot, control_error = safe_call(
        "control_center_snapshot",
        lambda: telegram_bot._control_center_snapshot(user=user_id, days=days),
    )
    system_snapshot, system_error = safe_call(
        "system_audit_snapshot",
        lambda: telegram_bot._system_audit_snapshot(user_id),
    )
    finance_api_snapshot, finance_api_error = safe_call(
        "finance_api_status_snapshot",
        lambda: telegram_bot._finance_api_status_snapshot(user_id),
    )

    degraded_notes = [
        item
        for item in (
            financial_engine_error,
            business_metrics_error,
            director_error,
            kpi_error,
            advisor_error,
            decision_error,
            cfo_error,
            control_error,
            system_error,
            finance_api_error,
        )
        if item
    ]

    executive_summary = safe_text(
        director_snapshot.get("executive_summary")
        or (advisor_snapshot.get("business_state") or {}).get("summary")
        or "Command Center is available with partial backend data.",
        "Command Center is available with partial backend data.",
    )
    business_health_status = status_to_api(director_snapshot.get("business_health"))
    confidence_score = safe_int(
        director_snapshot.get("data_confidence")
        or advisor_snapshot.get("data_confidence")
        or kpi_snapshot.get("data_confidence"),
        50,
    )
    trust_score = safe_int(((control_snapshot.get("data") or {}).get("trust_score")), confidence_score)
    health_score_base = {
        "GOOD": 84,
        "WARNING": 62,
        "CRITICAL": 28,
        "UNKNOWN": 50,
    }[business_health_status]
    health_score = max(0, min(100, int(round((health_score_base + trust_score) / 2))))

    cfo_insights = list(cfo_snapshot.get("insights") or [])
    cfo_risks = list(cfo_snapshot.get("risks") or [])
    advisor_risks = list(advisor_snapshot.get("risks") or [])
    control_blockers = list(control_snapshot.get("known_blockers") or [])
    decision_actions = list(decision_snapshot.get("top_actions") or [])
    advisor_actions = list(advisor_snapshot.get("do_now") or [])
    cfo_actions = list(cfo_snapshot.get("actions") or [])

    what_happened: list[str] = []
    if executive_summary:
        what_happened.append(executive_summary)
    for entry in cfo_insights[:2]:
        message = safe_text((entry or {}).get("message"), "")
        if message:
            what_happened.append(message)
    what_happened = [item for item in what_happened if item][:3]

    why: list[str] = []
    for entry in cfo_risks[:2]:
        message = safe_text((entry or {}).get("message"), "")
        if message:
            why.append(message)
    why.extend([safe_text(item, "") for item in control_blockers[:2]])
    why = [item for item in why if item][:4]

    actions: list[str] = []
    for item in advisor_actions + decision_actions + cfo_actions:
        text = safe_text(item, "")
        if text and text not in actions:
            actions.append(text)
    actions = actions[:5]

    kpis = []
    for item in list(kpi_snapshot.get("kpis") or []):
        item = dict(item or {})
        title = safe_text(item.get("name"), "KPI")
        kpis.append(
            {
                "id": title.lower().replace(" ", "-"),
                "title": title,
                "value": safe_text(item.get("value"), "n/a"),
                "delta": safe_text(item.get("target") or item.get("basis"), "n/a"),
                "status": status_to_api(item.get("status")),
                "source": safe_text(item.get("basis") or item.get("group"), "UNKNOWN"),
            }
        )

    workspaces = [
        {
            "title": "Business",
            "href": "/business",
            "summary": "Director summary, risks, and operating context.",
            "status": status_to_api(((control_snapshot.get("business") or {}).get("director_status"))),
        },
        {
            "title": "Finance",
            "href": "/finance",
            "summary": "Official finance status, payout confidence, and coverage.",
            "status": status_to_api(((control_snapshot.get("finance") or {}).get("new_finance_api_status"))),
        },
        {
            "title": "Products",
            "href": "/products",
            "summary": "Cost coverage and SKU readiness signals.",
            "status": status_to_api(((control_snapshot.get("data") or {}).get("sku_registry_status"))),
        },
        {
            "title": "Advertising",
            "href": "/advertising",
            "summary": "Ads health and linkability quality.",
            "status": status_to_api(((control_snapshot.get("data") or {}).get("ads_status"))),
        },
        {
            "title": "System",
            "href": "/system",
            "summary": "Diagnostics, data trust, and runtime readiness.",
            "status": status_to_api(((control_snapshot.get("diagnostics") or {}).get("system_audit_status"))),
        },
    ]

    recent_events = [
        {
            "id": f"event-{index}",
            "title": f"Signal {index}",
            "detail": item,
            "status": business_health_status,
        }
        for index, item in enumerate(what_happened[:3], 1)
    ]

    critical_alerts = [
        {
            "id": f"alert-{index}",
            "title": "Attention required",
            "detail": safe_text(item),
            "status": "CRITICAL" if index <= 2 else "WARNING",
        }
        for index, item in enumerate(control_blockers[:3] + advisor_risks[:2], 1)
    ]

    today_actions = [
        {
            "id": f"action-{index}",
            "title": item,
            "owner": "Command Center",
            "eta": "Today",
            "status": "WARNING" if index == 1 else "GOOD",
        }
        for index, item in enumerate(actions[:4], 1)
    ]

    return {
        "product": PRODUCT_NAME,
        "screen": "command_center",
        "period": {
            "label": "current_month",
            "date_from": start_date,
            "date_to": end_date,
        },
        "business_health": {
            "score": health_score,
            "status": business_health_status,
            "summary": executive_summary,
            "confidence": confidence_score,
            "data_mode": "official" if business_metrics_snapshot.get("official_available") else (
                "operational" if business_metrics_snapshot.get("operational_available") else "partial"
            ),
        },
        "executive_brief": {
            "title": safe_text(
                (director_snapshot.get("main_action") or {}).get("title")
                or (advisor_snapshot.get("main_recommendation") or {}).get("title"),
                "Executive brief",
            ),
            "what_happened": what_happened or ["No executive summary was available."],
            "why": why or ["The current summary was assembled from partial backend evidence."],
            "actions": actions or ["Review system and finance workspaces for more detail."],
            "confidence": confidence_score,
            "sources": safe_list(director_snapshot.get("source_layers") or ["Director", "KPI", "Advisor v2"]),
        },
        "kpis": kpis,
        "workspaces": workspaces,
        "today_actions": today_actions,
        "critical_alerts": critical_alerts,
        "recent_events": recent_events,
        "system": {
            "status": safe_text((system_snapshot.get("health") or {}).get("verdict") or system_snapshot.get("verdict"), "UNKNOWN"),
            "finance_api": safe_text(finance_api_snapshot.get("status"), "UNKNOWN"),
            "last_updated": now_iso(),
            "degraded": bool(degraded_notes),
            "degraded_notes": degraded_notes,
        },
    }


def _cached_snapshot(key: str) -> dict[str, Any]:
    return get_stale_cache_value(key) or {}


def _workspace_payload(key: str, builder, user_id: int) -> dict[str, Any]:
    payload = _cached_snapshot(key)
    if payload:
        return normalize_business_payload(payload) if key == "business" else payload
    payload = builder(user_id)
    return normalize_business_payload(payload) if key == "business" else payload


def get_executive_payload_fast(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    business = _workspace_payload("business", get_business_payload, user_id)
    finance = _workspace_payload("finance", get_finance_payload, user_id)
    advertising = _workspace_payload("advertising", get_advertising_payload, user_id)
    products = _workspace_payload("products", get_products_payload, user_id)
    inventory = _workspace_payload("inventory", get_inventory_payload, user_id)
    advisor = _cached_snapshot("advisor")
    system = _cached_snapshot("system")
    decision_engine = get_decision_engine_payload(user_id)
    performance = get_performance_snapshot()

    business_summary = dict(business.get("summary") or {})
    finance_summary = dict(finance.get("summary") or {})
    finance_quality = dict(finance.get("quality") or {})
    finance_difference = dict(finance.get("difference") or {})
    advertising_summary = dict(advertising.get("summary") or {})
    products_summary = dict(products.get("summary") or {})
    inventory_summary = dict(inventory.get("summary") or {})
    advisor_summary = dict(advisor.get("summary") or {})
    business_has_data = any(
        business_summary.get(key) is not None
        for key in ("revenue", "profit", "margin", "orders", "returns", "averageOrderValue", "unitsSold")
    )
    finance_has_data = any(
        finance_summary.get(key) is not None for key in ("operatingProfit", "officialProfit", "difference", "trustScore")
    ) or finance_quality.get("coverage") is not None
    advertising_has_data = any(
        advertising_summary.get(key) is not None for key in ("advertisingSpend", "linkedSpend", "unlinkedSpend", "roas", "acos")
    )
    has_core_business_data = business_has_data or finance_has_data or advertising_has_data
    decision_summary = dict(decision_engine.get("summary") or {})
    decision_risk = dict(decision_engine.get("mainRisk") or {})
    decision_opportunity = dict(decision_engine.get("mainOpportunity") or {})
    decision_forecast = dict(decision_engine.get("forecast") or {})
    decision_changes = list(decision_engine.get("whatChanged") or [])
    decision_actions = list(decision_engine.get("todayActions") or [])
    business_health_status = status_to_api(
        decision_summary.get("status") or (business.get("healthStatus") if has_core_business_data else "UNKNOWN")
    )
    trust_score = safe_int(finance_summary.get("trustScore")) if finance_has_data else None
    health_score = (
        safe_int(
            business.get("healthScore"),
            max(35, min(95, int(round(((trust_score or 50) + (84 if business_health_status == "GOOD" else 58)) / 2)))),
        )
        if has_core_business_data
        else None
    )

    executive_summary = safe_text(
        decision_summary.get("message")
        or (system.get("controlCenter") or {}).get("summary")
        or (advisor.get("insights") or [{}])[0].get("summary")
        or _executive_summary(business_summary, finance_summary, finance_difference, advertising_summary),
        "Сводка руководителя появится после загрузки аналитики.",
    )
    if not has_core_business_data:
        executive_summary = "Данные по бизнесу, финансам и рекламе появятся после первой успешной синхронизации."
    what_happened = [safe_text((item or {}).get("message"), "") for item in decision_changes[:3]]
    if not any(what_happened):
        what_happened = [
            executive_summary,
        _localize_executive_text(finance_summary.get("status"), ""),
        _localize_executive_text(advertising_summary.get("status"), ""),
        ]
    what_happened = [item for item in what_happened if item][:3]

    why = [
        _localize_executive_text(decision_risk.get("reason"), ""),
        _localize_executive_text(decision_forecast.get("message"), ""),
        _localize_executive_text((finance.get("difference") or {}).get("reason"), ""),
        _localize_executive_text((inventory.get("health") or {}).get("warehouseStatus"), ""),
        _localize_executive_text((advisor.get("conversation") or {}).get("prompt"), ""),
    ]
    why = [item for item in why if item][:4]

    actions: list[str] = []
    for item in decision_actions:
        label = safe_text((item or {}).get("action") or (item or {}).get("message") or (item or {}).get("title"), "")
        if label and label not in actions:
            actions.append(label)
    for item in list(advisor.get("actions") or []):
        label = safe_text((item or {}).get("label"), "")
        if label and label not in actions:
            actions.append(label)
    for item in (
        "Откройте раздел финансов для сверки официальной прибыли.",
        "Проверьте давление по остаткам перед масштабированием спроса.",
        "Проверьте эффективность рекламы при текущих расходах.",
    ):
        if item not in actions:
            actions.append(item)
    actions = actions[:5]
    revenue_value = _first_number(business_summary.get("revenue"), finance_difference.get("revenue"))
    profit_value = _first_number(
        business_summary.get("profit"),
        finance_summary.get("operatingProfit"),
        finance_summary.get("officialProfit"),
    )
    margin_value = _first_number(
        business_summary.get("margin"),
        ((profit_value / revenue_value) * 100) if (revenue_value and profit_value is not None) else None,
    )
    orders_value = _first_number(business_summary.get("orders"))
    ad_spend_value = _first_number(advertising_summary.get("advertisingSpend"))
    roas_value = _first_number(advertising_summary.get("roas"))
    acos_value = _first_number(advertising_summary.get("acos"))

    kpis = [
        {
            "id": "revenue",
            "title": "Выручка",
            "value": _format_metric_value(revenue_value, "Нет данных"),
            "delta": safe_text(business.get("healthStatus"), "Бизнес"),
            "status": status_to_api(business.get("healthStatus")),
            "source": "business",
        },
        {
            "id": "profit",
            "title": "Операционная прибыль",
            "value": _format_metric_value(profit_value, "Нет данных"),
            "delta": safe_text(finance_summary.get("status"), "Сверено с финансами"),
            "status": status_to_api(finance_summary.get("health")),
            "source": "finance",
        },
        {
            "id": "margin",
            "title": "Маржинальность",
            "value": f"{_format_metric_value(margin_value)}%" if margin_value is not None else "Нет данных",
            "delta": safe_text(business.get("healthStatus"), "Бизнес"),
            "status": status_to_api(business.get("healthStatus")),
            "source": "business",
        },
        {
            "id": "orders",
            "title": "Заказы",
            "value": _format_metric_value(orders_value, "Нет данных"),
            "delta": safe_text(business.get("healthStatus"), "Бизнес"),
            "status": status_to_api(business.get("healthStatus")),
            "source": "business",
        },
        {
            "id": "advertising-spend",
            "title": "Расходы на рекламу",
            "value": _format_metric_value(ad_spend_value, "Нет данных"),
            "delta": safe_text(advertising_summary.get("status"), "Реклама"),
            "status": status_to_api(advertising_summary.get("adsHealth")),
            "source": "advertising",
        },
        {
            "id": "roas",
            "title": "ROAS",
            "value": _format_metric_value(roas_value, "Нет данных"),
            "delta": safe_text(advertising_summary.get("status"), "Реклама"),
            "status": status_to_api(advertising_summary.get("adsHealth")),
            "source": "advertising",
        },
        {
            "id": "acos",
            "title": "ACOS",
            "value": f"{_format_metric_value(acos_value)}%" if acos_value is not None else "Нет данных",
            "delta": safe_text(advertising_summary.get("status"), "Реклама"),
            "status": status_to_api(advertising_summary.get("adsHealth")),
            "source": "advertising",
        },
        {
            "id": "trust-score",
            "title": "Надежность данных",
            "value": f"{trust_score}/100" if trust_score is not None else "Нет данных",
            "delta": safe_text(finance_quality.get("confidence"), "Нет данных") if trust_score is not None else "Нет финансовых данных",
            "status": status_to_api(finance_summary.get("health")),
            "source": "finance",
        },
        {
            "id": "inventory-health",
            "title": "Состояние остатков",
            "value": safe_text(inventory_summary.get("inventoryHealth"), "Нет данных"),
            "delta": safe_text((inventory.get("health") or {}).get("forecastConfidence"), "Нет данных"),
            "status": status_to_api(inventory_summary.get("inventoryHealth")),
            "source": "inventory",
        },
    ]

    workspaces = [
        {"title": "Business", "href": "/business", "summary": "Тренды выручки и прибыли из рабочего backend-контура.", "status": status_to_api(business.get("healthStatus"))},
        {"title": "Finance", "href": "/finance", "summary": "Надежность, покрытие и объяснение расхождений.", "status": status_to_api(finance_summary.get("health"))},
        {"title": "Advertising", "href": "/advertising", "summary": "Расходы, ROAS, ACOS и состояние рекламы.", "status": status_to_api(advertising_summary.get("adsHealth"))},
        {"title": "Products", "href": "/products", "summary": "SKU-сигналы, приоритеты и риски ассортимента.", "status": "GOOD" if products_summary.get("skuCount") else "UNKNOWN"},
        {"title": "Inventory", "href": "/inventory", "summary": "Покрытие остатков, пополнение и готовность складов.", "status": status_to_api(inventory_summary.get("inventoryHealth"))},
        {"title": "System", "href": "/system", "summary": "Диагностика runtime и стабильность API.", "status": status_to_api(system.get("status"))},
    ]

    alerts: list[dict[str, Any]] = []
    for payload, title in (
        (finance, "Финансы требуют внимания"),
        (products, "Обнаружен товарный риск"),
        (inventory, "Обнаружено давление по остаткам"),
    ):
        for item in list(payload.get("alerts") or [])[:2]:
            alerts.append(
                {
                    "id": f"alert-{len(alerts) + 1}",
                    "title": title,
                    "detail": safe_text((item or {}).get("description") or (item or {}).get("title"), "Откройте раздел для подробностей."),
                    "status": "WARNING",
                }
            )
    if not alerts and performance.get("/api/executive", {}).get("last_error"):
        alerts.append(
            {
                "id": "alert-runtime",
                "title": "Предупреждение executive runtime",
                "detail": safe_text(performance.get("/api/executive", {}).get("last_error"), "Кэш executive-прослойки прогревается."),
                "status": "WARNING",
            }
        )
    if decision_risk:
        alerts.insert(
            0,
            {
                "id": safe_text(decision_risk.get("id"), "alert-decision-risk"),
                "title": safe_text(decision_risk.get("title"), "Управленческий риск"),
                "detail": safe_text(decision_risk.get("reason") or decision_risk.get("message"), "Проверьте выделенный риск."),
                "status": "CRITICAL" if safe_text(decision_risk.get("severity"), "medium").lower() == "critical" else "WARNING",
            },
        )

    recent_events = [
        {
            "id": safe_text((item or {}).get("id"), f"event-{index}"),
                "title": safe_text((item or {}).get("title"), f"Сигнал {index}"),
            "detail": safe_text((item or {}).get("message"), executive_summary),
            "status": status_to_api((item or {}).get("severity")),
        }
        for index, item in enumerate(decision_changes[:3], 1)
    ]
    if not recent_events:
        recent_events = [
            {"id": f"event-{index}", "title": f"Signal {index}", "detail": item, "status": business_health_status}
            for index, item in enumerate(what_happened, 1)
        ]
    today_actions: list[dict[str, Any]] = []
    for index, item in enumerate(decision_actions[:4], 1):
        today_actions.append(
            {
                "id": safe_text((item or {}).get("id"), f"action-{index}"),
                "title": safe_text((item or {}).get("message") or (item or {}).get("title") or (item or {}).get("action"), "Проверьте действие"),
                "owner": safe_text((item or {}).get("source"), "Command Center"),
                "eta": "Today",
                "status": status_to_api((item or {}).get("severity")),
            }
        )
    if not today_actions:
        today_actions = [
            {"id": f"action-{index}", "title": item, "owner": "Command Center", "eta": "Today", "status": "GOOD" if index > 1 else "WARNING"}
            for index, item in enumerate(actions[:4], 1)
        ]

    return {
        "product": PRODUCT_NAME,
        "screen": "command_center",
        "period": {
            "label": "current_month",
            "date_from": start_date,
            "date_to": end_date,
        },
        "business_health": {
            "score": health_score,
            "status": business_health_status,
            "summary": executive_summary,
            "confidence": trust_score,
            "data_mode": "live" if (business or finance or advertising or products or inventory) else "degraded",
        },
        "executive_brief": {
            "title": safe_text(decision_summary.get("title") or (advisor.get("insights") or [{}])[0].get("title"), "Сводка руководителя"),
            "what_happened": what_happened or ["Аналитика backend еще загружается."],
            "why": why or ["Executive-слой использует текущую аналитику рабочих разделов."],
            "actions": actions or ["Откройте разделы «Финансы» или «Бизнес», чтобы проверить исходные метрики."],
            "confidence": safe_int(decision_summary.get("confidence"), trust_score),
            "sources": list(decision_engine.get("sources") or ["business", "finance", "advertising", "products", "inventory", "advisor", "system"]),
        },
        "kpis": kpis,
        "workspaces": workspaces,
        "today_actions": today_actions,
        "critical_alerts": alerts[:5],
        "recent_events": recent_events,
        "decision_engine": decision_engine,
        "system": {
            "status": safe_text(system.get("status"), "UNKNOWN"),
            "finance_api": safe_text((system.get("financeApi") or {}).get("status"), safe_text(finance_summary.get("health"), "UNKNOWN")),
            "last_updated": now_iso(),
            "degraded": not bool(business or finance or advertising or products or inventory),
            "degraded_notes": [] if (business or finance or advertising or products or inventory) else ["Аналитика рабочих разделов backend еще не готова."],
        },
    }
