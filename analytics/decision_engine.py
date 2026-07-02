from __future__ import annotations

from typing import Any

from analytics.advertising import get_advertising_payload
from analytics.advisor import get_advisor_payload_fast
from analytics.business import get_business_payload, normalize_business_payload
from analytics.cache import get_stale_cache_value
from analytics.common import DEFAULT_USER_ID, current_month_days, safe_float, safe_int, safe_text
from analytics.finance import get_finance_payload
from analytics.forecast_engine import build_forecast_payload
from analytics.inventory import get_inventory_payload
from analytics.products import get_products_payload
from analytics.system import get_system_payload


DECISION_LABELS = {
    "SCALE": "Масштабировать",
    "REDUCE": "Снизить расходы",
    "PAUSE": "Остановить",
    "WATCH": "Наблюдать",
    "RESTOCK": "Пополнить остатки",
    "CHECK_FINANCE": "Проверить финансы",
    "CHECK_ADS": "Проверить рекламу",
    "CHECK_INVENTORY": "Проверить остатки",
    "FIX_DATA": "Исправить данные",
    "WAIT_FOR_DATA": "Дождаться синхронизации",
}

SEVERITY_SCORES = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

PRIORITY_SCORES = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

IMPACT_SCORES = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _confidence_score(value: Any) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, int(round(float(value)))))
    normalized = safe_text(value, "").strip().lower()
    if normalized in {"high", "высокая", "высокий"}:
        return 85
    if normalized in {"medium", "средняя", "средний"}:
        return 65
    if normalized in {"low", "низкая", "низкий"}:
        return 40
    if normalized in {"unavailable", "unknown", "none", ""}:
        return 0
    return 50


def _decision_title(decision_type: str, related_sku: str | None = None) -> str:
    base = DECISION_LABELS.get(decision_type, "Действие")
    return f"{base}: {related_sku}" if related_sku else base


def _signal_score(item: dict[str, Any]) -> int:
    severity = SEVERITY_SCORES.get(safe_text(item.get("severity"), "low").lower(), 0)
    priority = PRIORITY_SCORES.get(safe_text(item.get("priority"), "low").lower(), 0)
    impact = IMPACT_SCORES.get(safe_text(item.get("expectedImpact"), "low").lower(), 0)
    confidence = _confidence_score(item.get("confidence")) // 25
    return severity * 4 + priority * 3 + impact * 2 + confidence


def _build_signal(
    *,
    signal_id: str,
    decision_type: str,
    message: str,
    reason: str,
    source: str,
    severity: str = "medium",
    priority: str = "medium",
    expected_impact: str = "medium",
    confidence: int | str | None = None,
    related_sku: str | None = None,
    related_metric: str | None = None,
    action: str | None = None,
    category: str = "action",
) -> dict[str, Any]:
    resolved_confidence = None if confidence is None else _confidence_score(confidence)
    return {
        "id": signal_id,
        "type": decision_type,
        "label": DECISION_LABELS.get(decision_type, decision_type),
        "title": _decision_title(decision_type, related_sku),
        "message": message,
        "severity": severity,
        "priority": priority,
        "expectedImpact": expected_impact,
        "confidence": resolved_confidence,
        "reason": reason,
        "action": action or message,
        "source": source,
        "relatedSku": related_sku,
        "relatedMetric": related_metric,
        "category": category,
    }


def _evidence(label: str, metric: str, value: Any, source: str, confidence: int | None, reason: str, related_sku: str | None = None, related_metric: str | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "metric": metric,
        "value": value,
        "source": source,
        "confidence": confidence,
        "reason": reason,
        "relatedSku": related_sku,
        "relatedMetric": related_metric or metric,
    }


def _product_decision_type(item: dict[str, Any]) -> str:
    normalized = safe_text(item.get("id"), "").lower()
    recommendation = safe_text(item.get("recommendation"), "").lower()
    if "pause" in normalized or "останов" in recommendation:
        return "PAUSE"
    if "reduce" in normalized or "сниз" in recommendation:
        return "REDUCE"
    if "scale" in normalized or "масштаб" in recommendation:
        return "SCALE"
    if "watch" in normalized or "наблюд" in recommendation:
        return "WATCH"
    return "WATCH"


def _product_signal(item: dict[str, Any]) -> dict[str, Any]:
    decision_type = _product_decision_type(item)
    is_opportunity = decision_type == "SCALE"
    return _build_signal(
        signal_id=safe_text(item.get("id"), "product-signal"),
        decision_type=decision_type,
        message=safe_text(item.get("recommendation"), "Проверьте товарный сигнал."),
        reason=safe_text(item.get("reason"), "SKU Action Plan выделил этот товар как приоритетный."),
        source="products",
        severity="medium" if is_opportunity else safe_text(item.get("priority"), "medium").lower(),
        priority=safe_text(item.get("priority"), "medium").lower(),
        expected_impact="high" if is_opportunity else "medium",
        confidence=item.get("confidence"),
        related_sku=safe_text(item.get("sku"), "") or None,
        related_metric="sku_action_plan",
        action=safe_text(item.get("expectedEffect"), safe_text(item.get("recommendation"), "Проверьте товарный сигнал.")),
        category="opportunity" if is_opportunity else "risk",
    )


def _has_business_data(business: dict[str, Any]) -> bool:
    summary = dict(business.get("summary") or {})
    return any(summary.get(key) is not None for key in ("revenue", "profit", "margin", "orders", "unitsSold"))


def _has_finance_data(finance: dict[str, Any]) -> bool:
    summary = dict(finance.get("summary") or {})
    quality = dict(finance.get("quality") or {})
    return any(summary.get(key) is not None for key in ("operatingProfit", "officialProfit", "difference", "trustScore")) or quality.get("coverage") is not None


def _has_advertising_data(advertising: dict[str, Any]) -> bool:
    summary = dict(advertising.get("summary") or {})
    return any(summary.get(key) is not None for key in ("advertisingSpend", "linkedSpend", "unlinkedSpend", "roas", "acos"))


def _forecast_payload(business: dict[str, Any], finance: dict[str, Any], main_opportunity: dict[str, Any] | None) -> dict[str, Any]:
    revenue_trend = safe_float(((business.get("trends") or {}).get("revenue")))
    profit = safe_float(((business.get("summary") or {}).get("profit")))
    operating_profit = safe_float(((finance.get("summary") or {}).get("operatingProfit")))
    resolved_profit = profit if profit is not None else operating_profit
    if resolved_profit is None and revenue_trend is None:
        return {
            "status": "insufficient_data",
            "message": "Для прогноза нужно больше данных за период.",
            "profit": None,
            "profitDirection": None,
            "riskLevel": "unknown",
            "expectedImpact": None,
            "confidence": None,
        }

    direction = "up" if (revenue_trend or 0) > 0 else ("down" if (revenue_trend or 0) < 0 else "flat")
    return {
        "status": "ready",
        "message": "Текущий прогноз основан на последней бизнес- и финансовой динамике." if resolved_profit is not None else "Прогноз собран по доступной динамике выручки.",
        "profit": resolved_profit,
        "profitDirection": direction,
        "riskLevel": "medium" if direction == "flat" else ("low" if direction == "up" else "high"),
        "expectedImpact": safe_text((main_opportunity or {}).get("expectedImpact"), None),
        "confidence": 70 if resolved_profit is not None else 55,
    }


def _forecast_signal_from_row(
    *,
    item: dict[str, Any],
    signal_id: str,
    decision_type: str,
    severity: str,
    priority: str,
    expected_impact: str,
    category: str,
) -> dict[str, Any]:
    return _build_signal(
        signal_id=signal_id,
        decision_type=decision_type,
        message=safe_text(item.get("title"), "Прогнозный сигнал требует внимания."),
        reason=safe_text(item.get("reason"), "Сигнал сформирован на основе прогноза."),
        source="forecast",
        severity=severity,
        priority=priority,
        expected_impact=expected_impact,
        confidence=item.get("confidence"),
        related_sku=safe_text(item.get("sku"), "") or None,
        related_metric=safe_text(item.get("metric"), "forecast"),
        action=safe_text(item.get("action"), safe_text(item.get("title"), "Откройте прогноз и проверьте сценарий.")),
        category=category,
    )


def _forecast_payload_from_engine(
    forecast_payload: dict[str, Any],
    main_risk: dict[str, Any] | None,
    main_opportunity: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = dict(forecast_payload.get("summary") or {})
    sales_forecast = dict(forecast_payload.get("salesForecast") or {})
    profit_forecast = dict(forecast_payload.get("profitForecast") or {})
    inventory_forecast = dict(forecast_payload.get("inventoryForecast") or {})
    periods = dict(forecast_payload.get("periods") or {})
    seven_days = dict(periods.get("sevenDays") or {})

    status = safe_text(summary.get("status"), "insufficient_data")
    expected_profit = safe_float(profit_forecast.get("expectedOperatingProfit"))
    expected_revenue = safe_float(seven_days.get("expectedRevenue"))
    expected_orders = safe_float(seven_days.get("expectedOrders"))
    expected_units = safe_float(seven_days.get("expectedUnits"))
    risk_level = safe_text(summary.get("riskLevel"), None)
    confidence = profit_forecast.get("confidence")
    if confidence is None:
        confidence = sales_forecast.get("confidence")
    if confidence is None:
        confidence = summary.get("confidence")

    if status == "insufficient_data":
        return {
            "status": status,
            "message": "Для прогноза нужно больше данных по продажам, рекламе и прибыли.",
            "profit": None,
            "profitDirection": None,
            "riskLevel": "unknown",
            "expectedImpact": safe_text((main_opportunity or {}).get("expectedImpact"), None),
            "confidence": None,
            "expectedRevenue": None,
            "expectedOrders": None,
            "expectedUnits": None,
            "primaryRisk": safe_text((main_risk or {}).get("message"), None),
            "recommendedAction": safe_text((main_opportunity or {}).get("action"), safe_text((main_risk or {}).get("action"), None)),
        }

    trend = safe_text(seven_days.get("trend"), "").lower()
    if "рост" in trend:
        direction = "up"
    elif "сниж" in trend:
        direction = "down"
    else:
        direction = "flat"

    primary_risk = safe_text((inventory_forecast.get("mainRisk") or {}).get("title"), None) or safe_text((main_risk or {}).get("message"), None)
    recommended_action = safe_text((main_opportunity or {}).get("action"), None) or safe_text((main_risk or {}).get("action"), None)
    message = safe_text(summary.get("headline"), None) or safe_text(
        summary.get("statusText"),
        "Прогноз обновлен на основе текущей динамики бизнеса.",
    )
    if status == "degraded":
        message = safe_text(summary.get("statusText"), message)
    summary_parts = []
    if expected_revenue is not None:
        summary_parts.append(f"7 дней: выручка около {expected_revenue:.0f}")
    if expected_profit is not None:
        summary_parts.append(f"операционная прибыль около {expected_profit:.0f}")
    if expected_orders is not None:
        summary_parts.append(f"заказы около {expected_orders:.0f}")
    if primary_risk:
        summary_parts.append(f"риск: {primary_risk}")
    if recommended_action:
        summary_parts.append(f"действие: {recommended_action}")
    if summary_parts:
        message = f"{message} {'; '.join(summary_parts)}."

    return {
        "status": status,
        "message": message,
        "profit": expected_profit,
        "profitDirection": direction,
        "riskLevel": risk_level or ("medium" if direction == "flat" else ("low" if direction == "up" else "high")),
        "expectedImpact": safe_text((main_opportunity or {}).get("expectedImpact"), None),
        "confidence": confidence,
        "expectedRevenue": expected_revenue,
        "expectedOrders": expected_orders,
        "expectedUnits": expected_units,
        "primaryRisk": primary_risk,
        "recommendedAction": recommended_action,
    }


def _cached_reports_snapshot() -> dict[str, Any]:
    return get_stale_cache_value("reports") or {}


def get_decision_engine_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    business = normalize_business_payload(get_business_payload(user_id))
    finance = get_finance_payload(user_id)
    advertising = get_advertising_payload(user_id)
    products = get_products_payload(user_id)
    inventory = get_inventory_payload(user_id)
    advisor = get_advisor_payload_fast(user_id)
    system = get_system_payload(user_id)
    forecast_payload = build_forecast_payload(
        user_id=user_id,
        business=business,
        finance=finance,
        advertising=advertising,
        inventory=inventory,
        products=products,
    )
    reports = _cached_reports_snapshot()
    start_date, end_date = current_month_days()

    has_business_data = _has_business_data(business)
    has_finance_data = _has_finance_data(finance)
    has_advertising_data = _has_advertising_data(advertising)
    has_core_data = has_business_data or has_finance_data or has_advertising_data

    risk_candidates: list[dict[str, Any]] = []
    opportunity_candidates: list[dict[str, Any]] = []
    today_actions: list[dict[str, Any]] = []
    what_changed: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    business_summary = dict(business.get("summary") or {})
    finance_summary = dict(finance.get("summary") or {})
    finance_quality = dict(finance.get("quality") or {})
    advertising_summary = dict(advertising.get("summary") or {})
    inventory_summary = dict(inventory.get("summary") or {})
    inventory_health = dict(inventory.get("health") or {})
    inventory_items = list(inventory.get("items") or [])

    if not has_core_data:
        today_actions = [
            _build_signal(
                signal_id="action-sync-sales",
                decision_type="WAIT_FOR_DATA",
                message="Синхронизируйте продажи, чтобы получить бизнес-выводы.",
                reason="Без данных по продажам AI Director не может оценить выручку, заказы и маржу.",
                source="business",
                severity="medium",
                priority="high",
                expected_impact="high",
                confidence=85,
                related_metric="revenue",
            ),
            _build_signal(
                signal_id="action-check-finance",
                decision_type="CHECK_FINANCE",
                message="Проверьте подключение финансов Wildberries.",
                reason="Финансовые данные Wildberries пока недоступны. Операционная аналитика продолжает работать.",
                source="finance",
                severity="medium",
                priority="high",
                expected_impact="medium",
                confidence=80,
                related_metric="official_profit",
            ),
            _build_signal(
                signal_id="action-load-ads",
                decision_type="CHECK_ADS",
                message="Загрузите рекламные данные для оценки эффективности кампаний.",
                reason="Без рекламных данных нельзя выделить кампании для масштабирования или снижения расходов.",
                source="advertising",
                severity="low",
                priority="medium",
                expected_impact="medium",
                confidence=75,
                related_metric="advertising_spend",
            ),
        ]
        evidence = [
            _evidence("Продажи", "Revenue", None, "business", 85, "В выбранном периоде нет загруженных бизнес-агрегатов."),
            _evidence("Финансы", "Official Profit", None, "finance", 80, "Финансовые данные Wildberries пока недоступны."),
            _evidence("Реклама", "ROAS", None, "advertising", 75, "Рекламные данные пока не синхронизированы."),
        ]
        return {
            "summary": {
                "title": "AI Director",
                "status": "UNKNOWN",
                "code": "insufficient_data",
                "message": "Недостаточно данных, чтобы сформировать управленческий вывод. Сначала завершите синхронизацию продаж, финансов и рекламы.",
                "confidence": None,
            },
            "whatChanged": [],
            "mainRisk": None,
            "mainOpportunity": None,
            "todayActions": today_actions,
            "forecast": _forecast_payload_from_engine(forecast_payload, None, None),
                "message": "Для прогноза нужно больше данных за период.",
            "evidence": evidence,
            "sources": ["business", "finance", "advertising", "products", "inventory", "advisor", "reports", "system"],
            "period": {"date_from": start_date, "date_to": end_date},
        }

    for item in list(products.get("recommendations") or []):
        signal = _product_signal(dict(item or {}))
        if signal["category"] == "opportunity":
            opportunity_candidates.append(signal)
        else:
            risk_candidates.append(signal)
        today_actions.append(signal)

    if not has_finance_data:
        risk_candidates.append(
            _build_signal(
                signal_id="finance-missing",
                decision_type="CHECK_FINANCE",
                message="Проверьте подключение финансов Wildberries.",
                reason="Финансовые данные Wildberries пока недоступны. Операционная аналитика продолжает работать.",
                source="finance",
                severity="medium",
                priority="high",
                expected_impact="medium",
                confidence=80,
                related_metric="official_profit",
                category="risk",
            )
        )
    else:
        trust_score = safe_int(finance_summary.get("trustScore"))
        if trust_score is not None and trust_score < 60:
            risk_candidates.append(
                _build_signal(
                    signal_id="finance-trust",
                    decision_type="CHECK_FINANCE",
                    message="Проверьте расхождение финансов перед управленческими решениями.",
                    reason=safe_text((finance.get("difference") or {}).get("reason"), "Точность финансовой сверки пока ограничена."),
                    source="finance",
                    severity="high",
                    priority="high",
                    expected_impact="high",
                    confidence=trust_score,
                    related_metric="trust_score",
                    category="risk",
                )
            )
            evidence.append(
                _evidence(
                    "Надежность финансов",
                    "Trust Score",
                    f"{trust_score}/100",
                    "finance",
                    trust_score,
                    safe_text((finance.get("difference") or {}).get("reason"), "Финансовая сверка требует внимания."),
                )
            )

    if not has_advertising_data:
        risk_candidates.append(
            _build_signal(
                signal_id="ads-missing",
                decision_type="CHECK_ADS",
                message="Загрузите рекламные данные для оценки эффективности кампаний.",
                reason="Без рекламных данных нельзя выделить кампании для масштабирования или снижения расходов.",
                source="advertising",
                severity="low",
                priority="medium",
                expected_impact="medium",
                confidence=75,
                related_metric="advertising_spend",
                category="risk",
            )
        )
    else:
        ads_health = safe_text(advertising_summary.get("adsHealth"), "Unknown")
        if ads_health not in {"GOOD", "LOW", "No advertising data available"}:
            risk_candidates.append(
                _build_signal(
                    signal_id="ads-check",
                    decision_type="CHECK_ADS",
                    message="Проверьте рекламные кампании с просадкой эффективности.",
                    reason=safe_text(advertising_summary.get("status"), "Реклама требует проверки."),
                    source="advertising",
                    severity="medium",
                    priority="medium",
                    expected_impact="medium",
                    confidence=60,
                    related_metric="roas",
                    category="risk",
                )
            )
        else:
            what_changed.append(
                {
                    "id": "ads-stable",
                    "type": "advertising",
                    "severity": "low",
                    "title": "Реклама стабильна",
                    "message": "Критичных действий по рекламе не требуется.",
                    "confidence": 70,
                    "source": "advertising",
                }
            )
        evidence.append(
            _evidence(
                "Рекламная эффективность",
                "Ads Health",
                advertising_summary.get("adsHealth"),
                "advertising",
                65,
                safe_text(advertising_summary.get("status"), "Статус рекламы рассчитан по текущей аналитике."),
            )
        )

    inventory_status = safe_text(inventory_summary.get("inventoryHealth"), "UNKNOWN")
    critical_inventory_item = next((item for item in inventory_items if safe_text(item.get("riskCode"), "") in {"OUT_OF_STOCK", "CRITICAL_LOW"}), None)
    low_inventory_item = next((item for item in inventory_items if safe_text(item.get("riskCode"), "") == "LOW"), None)
    scalable_inventory_item = next((item for item in inventory_items if bool(item.get("scaleAllowed"))), None)
    if critical_inventory_item:
        risk_candidates.append(
            _build_signal(
                signal_id=f"inventory-critical-{safe_text(critical_inventory_item.get('sku'), 'sku')}",
                decision_type="RESTOCK",
                message=safe_text(critical_inventory_item.get("recommendation"), "Срочно проверьте остатки."),
                reason=safe_text(critical_inventory_item.get("risk"), safe_text(inventory_health.get("warehouseStatus"), "Остатки требуют внимания.")),
                source="inventory",
                severity="critical",
                priority="critical",
                expected_impact="high",
                confidence=80,
                related_sku=safe_text(critical_inventory_item.get("sku"), "") or None,
                related_metric="coverage_days",
                action=safe_text(critical_inventory_item.get("recommendation"), "Срочно пополните остатки."),
                category="risk",
            )
        )
        if (safe_float(critical_inventory_item.get("linkedAdvertisingSpend")) or 0) > 0:
            risk_candidates.append(
                _build_signal(
                    signal_id=f"inventory-ads-{safe_text(critical_inventory_item.get('sku'), 'sku')}",
                    decision_type="CHECK_ADS",
                    message="Не масштабируйте рекламу до пополнения остатков.",
                    reason="SKU уже получает рекламный трафик, но запас близок к исчерпанию.",
                    source="inventory",
                    severity="high",
                    priority="high",
                    expected_impact="high",
                    confidence=78,
                    related_sku=safe_text(critical_inventory_item.get("sku"), "") or None,
                    related_metric="linked_advertising_spend",
                    action="Снизьте рекламное давление до пополнения склада.",
                    category="risk",
                )
            )
    elif low_inventory_item:
        risk_candidates.append(
            _build_signal(
                signal_id=f"inventory-low-{safe_text(low_inventory_item.get('sku'), 'sku')}",
                decision_type="CHECK_INVENTORY",
                message=safe_text(low_inventory_item.get("recommendation"), "Проверьте запас по SKU."),
                reason=safe_text(low_inventory_item.get("risk"), "Запас по SKU уменьшается быстрее целевого горизонта."),
                source="inventory",
                severity="medium",
                priority="medium",
                expected_impact="medium",
                confidence=68,
                related_sku=safe_text(low_inventory_item.get("sku"), "") or None,
                related_metric="coverage_days",
                category="risk",
            )
        )
    elif scalable_inventory_item:
        opportunity_candidates.append(
            _build_signal(
                signal_id=f"inventory-scale-{safe_text(scalable_inventory_item.get('sku'), 'sku')}",
                decision_type="SCALE",
                message=f"SKU {safe_text(scalable_inventory_item.get('sku'), 'товар')} можно масштабировать без риска дефицита.",
                reason="Запас покрывает безопасный горизонт и подтвержден текущей скоростью продаж.",
                source="inventory",
                severity="low",
                priority="medium",
                expected_impact="high",
                confidence=72,
                related_sku=safe_text(scalable_inventory_item.get("sku"), "") or None,
                related_metric="coverage_days",
                action="Масштабируйте SKU в пределах подтвержденного спроса.",
                category="opportunity",
            )
        )
    if not critical_inventory_item and not low_inventory_item and not scalable_inventory_item and inventory_status in {"DEGRADED", "WARNING"}:
        risk_candidates.append(
            _build_signal(
                signal_id="inventory-check",
                decision_type="CHECK_INVENTORY" if inventory_status == "DEGRADED" else "RESTOCK",
                message="Проверьте остатки и точки пополнения.",
                reason=safe_text(inventory_health.get("warehouseStatus"), "Инвентарные сигналы требуют внимания."),
                source="inventory",
                severity="medium",
                priority="medium",
                expected_impact="medium",
                confidence=55,
                related_metric="inventory_health",
                category="risk",
            )
        )

    system_status = safe_text(system.get("status"), "UNKNOWN")
    if system_status == "WARNING":
        risk_candidates.append(
            _build_signal(
                signal_id="system-fix-data",
                decision_type="FIX_DATA",
                message="Проверьте качество данных и runtime аналитики.",
                reason=safe_text((system.get("health") or {}).get("verdict"), "Системные проверки требуют внимания."),
                source="system",
                severity="low",
                priority="medium",
                expected_impact="medium",
                confidence=60,
                related_metric="data_quality",
                category="risk",
            )
        )

    revenue_trend = safe_float(((business.get("trends") or {}).get("revenue")))
    profit_trend = safe_float(((business.get("trends") or {}).get("profit")))
    if revenue_trend is not None:
        what_changed.append(
            {
                "id": "business-revenue-trend",
                "type": "business",
                "severity": "low" if revenue_trend >= 0 else "medium",
                "title": "Изменилась выручка",
                "message": f"Динамика выручки: {round(revenue_trend, 1)}% к предыдущему периоду.",
                "confidence": 70,
                "source": "business",
            }
        )
        evidence.append(
            _evidence(
                "Динамика бизнеса",
                "Revenue Trend",
                f"{round(revenue_trend, 1)}%",
                "business",
                70,
                "Изменение выручки рассчитано по бизнес-агрегатам.",
            )
        )
    if profit_trend is not None:
        what_changed.append(
            {
                "id": "business-profit-trend",
                "type": "finance",
                "severity": "low" if profit_trend >= 0 else "high",
                "title": "Изменилась прибыль",
                "message": f"Динамика прибыли: {round(profit_trend, 1)}% к предыдущему периоду.",
                "confidence": 65,
                "source": "finance",
            }
        )

    for item in list(advisor.get("recommendations") or [])[:2]:
        confidence = _confidence_score(item.get("confidence"))
        source = safe_text(item.get("source"), "advisor")
        signal = _build_signal(
            signal_id=safe_text(item.get("id"), "advisor-rec"),
            decision_type="WATCH",
            message=safe_text(item.get("title"), "Проверьте рекомендацию советника."),
            reason=safe_text(item.get("reason"), "Советник зафиксировал управленческий сигнал."),
            source=source,
            severity="medium" if confidence >= 60 else "low",
            priority="medium",
            expected_impact="medium",
            confidence=confidence,
            related_metric=source,
            action=safe_text(item.get("expectedEffect"), safe_text(item.get("title"), "Откройте соответствующий раздел.")),
            category="opportunity" if safe_text(item.get("priority"), "").lower() in {"medium", "low"} else "risk",
        )
        if signal["category"] == "opportunity":
            opportunity_candidates.append(signal)
        else:
            risk_candidates.append(signal)

    for index, item in enumerate(list(forecast_payload.get("risks") or [])[:3], start=1):
        risk_candidates.append(
            _forecast_signal_from_row(
                item=dict(item or {}),
                signal_id=safe_text(item.get("id"), f"forecast-risk-{index}"),
                decision_type="WATCH",
                severity="high" if index == 1 else "medium",
                priority="high" if index == 1 else "medium",
                expected_impact="high",
                category="risk",
            )
        )

    for index, item in enumerate(list(forecast_payload.get("opportunities") or [])[:3], start=1):
        opportunity_candidates.append(
            _forecast_signal_from_row(
                item=dict(item or {}),
                signal_id=safe_text(item.get("id"), f"forecast-opportunity-{index}"),
                decision_type="SCALE" if index == 1 else "WATCH",
                severity="low",
                priority="high" if index == 1 else "medium",
                expected_impact="high",
                category="opportunity",
            )
        )

    if not opportunity_candidates and has_business_data:
        top_products = list(business.get("topProducts") or [])
        if top_products:
            best = dict(top_products[0] or {})
            opportunity_candidates.append(
                _build_signal(
                    signal_id="business-top-product",
                    decision_type="SCALE",
                    message=f"Проверьте возможность масштабировать {safe_text(best.get('title'), 'сильный SKU')}.",
                    reason="Товар уже входит в число лидеров по выручке и прибыли.",
                    source="business",
                    severity="low",
                    priority="medium",
                    expected_impact="high",
                    confidence=70,
                    related_sku=safe_text(best.get("sku"), "") or None,
                    related_metric="revenue",
                    category="opportunity",
                )
            )

    risk_candidates = sorted(risk_candidates, key=_signal_score, reverse=True)
    opportunity_candidates = sorted(opportunity_candidates, key=_signal_score, reverse=True)
    today_actions = sorted(today_actions + risk_candidates[:2] + opportunity_candidates[:2], key=_signal_score, reverse=True)

    main_risk = risk_candidates[0] if risk_candidates else None
    main_opportunity = opportunity_candidates[0] if opportunity_candidates else None
    forecast = _forecast_payload_from_engine(forecast_payload, main_risk, main_opportunity)
    confidence_values = [item.get("confidence") for item in [main_risk, main_opportunity] if item and item.get("confidence") is not None]
    summary_confidence = int(round(sum(int(value) for value in confidence_values) / len(confidence_values))) if confidence_values else 65

    if main_risk and main_opportunity:
        message = f"Главный риск: {main_risk['message']}. Главная возможность: {main_opportunity['message']}."
        status = "WARNING"
    elif main_risk:
        message = f"Главный риск: {main_risk['message']}."
        status = "WARNING"
    elif main_opportunity:
        message = f"Главная возможность: {main_opportunity['message']}."
        status = "GOOD"
    else:
        message = "Критичных действий сегодня не требуется. Продолжайте наблюдать за динамикой бизнеса."
        status = "GOOD"

    report_count = safe_int(((reports.get("summary") or {}).get("reportCount")))
    if report_count is not None:
        evidence.append(
            _evidence(
                "Отчеты",
                "Reports",
                report_count,
                "reports",
                60,
                "Decision Engine использует текущие отчеты и кэшированные управленческие сводки.",
            )
        )

    return {
        "summary": {
            "title": "AI Director",
            "status": status,
            "code": "ready",
            "message": message,
            "confidence": summary_confidence,
        },
        "whatChanged": what_changed[:4],
        "mainRisk": main_risk,
        "mainOpportunity": main_opportunity,
        "todayActions": today_actions[:4],
        "forecast": forecast,
        "evidence": evidence[:6],
        "sources": ["business", "finance", "advertising", "products", "inventory", "advisor", "reports", "system"],
        "period": {"date_from": start_date, "date_to": end_date},
    }
