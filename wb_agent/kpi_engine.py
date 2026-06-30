"""Pure read-only KPI engine helpers.

This module must not call APIs, read databases, write cache, or recalculate
financial formulas. It evaluates prepared snapshot dicts into KPI statuses.
"""

KPI_ENGINE_ALLOWED_STATUS = ("OK", "PARTIAL", "INSUFFICIENT_DATA")
KPI_ALLOWED_GROUPS = ("FINANCE", "SALES", "ADS", "SKU", "DATA_QUALITY", "CASHFLOW")
KPI_ALLOWED_ITEM_STATUSES = ("GOOD", "NORMAL", "WARNING", "CRITICAL", "UNKNOWN")
KPI_ALLOWED_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")

__all__ = [
    "KPI_ENGINE_ALLOWED_STATUS",
    "KPI_ALLOWED_GROUPS",
    "KPI_ALLOWED_ITEM_STATUSES",
    "KPI_ALLOWED_CONFIDENCE",
    "build_kpi_snapshot",
    "kpi_engine_text",
]


def _float_or_none(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _int_or_none(value):
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _item(name, group, value, unit, target, status, message, basis, confidence):
    return {
        "name": str(name),
        "group": str(group),
        "value": value,
        "unit": str(unit),
        "target": str(target),
        "status": str(status),
        "message": str(message),
        "basis": str(basis),
        "confidence": str(confidence),
    }


def _dedup_texts(items):
    result = []
    seen = set()
    for item in list(items or []):
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _status_counts(kpis):
    summary = {
        "total_kpis": len(kpis),
        "good_count": 0,
        "normal_count": 0,
        "warning_count": 0,
        "critical_count": 0,
        "unknown_count": 0,
        "overall_status": "UNKNOWN",
    }
    for item in list(kpis or []):
        status = str(item.get("status") or "UNKNOWN")
        if status == "GOOD":
            summary["good_count"] += 1
        elif status == "NORMAL":
            summary["normal_count"] += 1
        elif status == "WARNING":
            summary["warning_count"] += 1
        elif status == "CRITICAL":
            summary["critical_count"] += 1
        else:
            summary["unknown_count"] += 1
    if summary["critical_count"] > 0:
        summary["overall_status"] = "CRITICAL"
    elif summary["warning_count"] > 0:
        summary["overall_status"] = "WARNING"
    elif summary["unknown_count"] > 0 and summary["total_kpis"] > 0:
        summary["overall_status"] = "NORMAL"
    elif summary["good_count"] > 0 or summary["normal_count"] > 0:
        summary["overall_status"] = "GOOD"
    return summary


def build_kpi_snapshot(
    period_snapshot=None,
    unified_data_snapshot=None,
    business_metrics_snapshot=None,
    financial_engine_snapshot=None,
    ads_snapshot=None,
    sales_snapshot=None,
    sku_registry_snapshot=None,
):
    period_snapshot = dict(period_snapshot or {})
    unified_data_snapshot = dict(unified_data_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    ads_snapshot = dict(ads_snapshot or {})
    sales_snapshot = dict(sales_snapshot or {})
    sku_registry_snapshot = dict(sku_registry_snapshot or {})

    kpis = []
    warnings = []

    unified_finance = dict(unified_data_snapshot.get("finance") or {})
    unified_quality = dict(unified_data_snapshot.get("quality") or {})
    unified_trust = dict(unified_data_snapshot.get("trust") or {})
    unified_ads = dict(unified_data_snapshot.get("advertising") or {})
    unified_costs = dict(unified_data_snapshot.get("costs") or {})
    unified_payments = dict(unified_data_snapshot.get("payments") or {})

    finance_status = str(
        financial_engine_snapshot.get("status")
        or business_metrics_snapshot.get("official_status")
        or unified_finance.get("status")
        or "UNAVAILABLE"
    )
    official_net_profit = business_metrics_snapshot.get("official_net_profit")
    if official_net_profit is None:
        official_net_profit = financial_engine_snapshot.get("official_net_profit")
    official_available = bool(business_metrics_snapshot.get("official_available")) or official_net_profit is not None
    operational_available = bool(business_metrics_snapshot.get("operational_available"))
    ads_health = str(business_metrics_snapshot.get("advertising_health") or unified_ads.get("status") or ads_snapshot.get("status") or "UNKNOWN")
    ads_linkability = _float_or_none(unified_ads.get("linkability_percent"))
    if ads_linkability is None:
        ads_linkability = _float_or_none(ads_snapshot.get("linkability_percent"))
    data_quality_score = _float_or_none(business_metrics_snapshot.get("data_quality_score"))
    if data_quality_score is None:
        data_quality_score = _float_or_none(unified_quality.get("overall_score"))
    trust_score = _int_or_none(business_metrics_snapshot.get("trust_score"))
    if trust_score is None:
        trust_score = _int_or_none(unified_trust.get("overall_trust"))
    sku_cost_coverage = _float_or_none(business_metrics_snapshot.get("cost_coverage_percent"))
    if sku_cost_coverage is None:
        sku_cost_coverage = _float_or_none(financial_engine_snapshot.get("cost_coverage_percent"))
    if sku_cost_coverage is None:
        sku_cost_coverage = _float_or_none(sku_registry_snapshot.get("coverage_percent"))
    payment_status = str(unified_payments.get("status") or sales_snapshot.get("status") or "UNKNOWN")
    data_confidence = str(
        business_metrics_snapshot.get("data_confidence")
        or ("HIGH" if (trust_score is not None and trust_score >= 85) else "MEDIUM" if (trust_score is not None and trust_score >= 60) else "LOW")
    )

    if finance_status in ("MATCHED", "OK"):
        kpis.append(_item("Finance API availability", "FINANCE", finance_status, "STATUS", "official finance available", "GOOD", "Финансовый контур доступен для официальной проверки.", f"financial_engine.status={finance_status}", "HIGH"))
    elif finance_status in ("RATE_LIMIT", "DETAIL_REQUIRED", "PARTIAL", "PARTIAL_COST_MISSING"):
        kpis.append(_item("Finance API availability", "FINANCE", finance_status, "STATUS", "official finance available", "WARNING", "Финансовый контур доступен частично и требует повторной проверки.", f"financial_engine.status={finance_status}", "MEDIUM"))
        warnings.append("Finance KPI warning: official financial layer is partially unavailable.")
    elif finance_status in ("FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "API_ENDPOINT_ERROR", "ERROR"):
        kpis.append(_item("Finance API availability", "FINANCE", finance_status, "STATUS", "official finance available", "CRITICAL", "Финансовый контур недоступен для подтверждения официального результата.", f"financial_engine.status={finance_status}", "LOW"))
        warnings.append("Finance KPI critical: official financial layer is unavailable.")
    else:
        kpis.append(_item("Finance API availability", "FINANCE", finance_status, "STATUS", "official finance available", "UNKNOWN", "Недостаточно данных для оценки финансового контура.", f"financial_engine.status={finance_status}", "LOW"))

    if official_available:
        kpis.append(_item("Official profit availability", "FINANCE", official_net_profit, "RUB", "official net profit available", "GOOD", "Официальная чистая прибыль доступна.", "business_metrics.official_net_profit", "HIGH"))
    else:
        kpis.append(_item("Official profit availability", "FINANCE", None, "RUB", "official net profit available", "WARNING", "Официальная чистая прибыль пока недоступна.", "business_metrics.official_available=false", "MEDIUM"))

    if operational_available and not official_available:
        kpis.append(_item("Operational estimate safety", "FINANCE", "operational_only", "STATUS", "official and operational clearly separated", "WARNING", "Операционная оценка не является официальной прибылью.", "operational_available=true and official_available=false", "HIGH"))
    elif official_available:
        kpis.append(_item("Operational estimate safety", "FINANCE", "safe", "STATUS", "official available", "GOOD", "Официальный и операционный контуры не конфликтуют.", "official_available=true", "HIGH"))
    else:
        kpis.append(_item("Operational estimate safety", "FINANCE", "unknown", "STATUS", "official available", "UNKNOWN", "Недостаточно данных для проверки разделения official/operational.", "insufficient data", "LOW"))

    if ads_health == "HIGH":
        kpis.append(_item("Ads health", "ADS", ads_health, "STATUS", "HIGH", "GOOD", "Качество рекламных данных высокое.", "business_metrics.advertising_health", "HIGH"))
    elif ads_health in ("MEDIUM", "PARTIAL"):
        kpis.append(_item("Ads health", "ADS", ads_health, "STATUS", "HIGH", "WARNING", "Рекламные данные требуют осторожной интерпретации.", "business_metrics.advertising_health", "MEDIUM"))
    elif ads_health in ("LOW", "ERROR"):
        kpis.append(_item("Ads health", "ADS", ads_health, "STATUS", "HIGH", "CRITICAL", "Качество рекламных данных низкое.", "business_metrics.advertising_health", "LOW"))
    else:
        kpis.append(_item("Ads health", "ADS", ads_health, "STATUS", "HIGH", "UNKNOWN", "Нет достаточных данных по рекламному здоровью.", "business_metrics.advertising_health", "LOW"))

    if ads_linkability is None:
        kpis.append(_item("Ads linkability", "ADS", None, "PERCENT", ">=95%", "UNKNOWN", "Нет данных по привязке рекламы к SKU.", "udl.advertising.linkability_percent", "LOW"))
    elif ads_linkability >= 95:
        kpis.append(_item("Ads linkability", "ADS", ads_linkability, "PERCENT", ">=95%", "GOOD", "Привязка рекламы к SKU высокая.", "udl.advertising.linkability_percent", "HIGH"))
    elif ads_linkability >= 80:
        kpis.append(_item("Ads linkability", "ADS", ads_linkability, "PERCENT", ">=95%", "WARNING", "Привязка рекламы к SKU неполная.", "udl.advertising.linkability_percent", "MEDIUM"))
    else:
        kpis.append(_item("Ads linkability", "ADS", ads_linkability, "PERCENT", ">=95%", "CRITICAL", "Привязка рекламы к SKU слишком низкая.", "udl.advertising.linkability_percent", "LOW"))

    if data_quality_score is None:
        kpis.append(_item("Data quality score", "DATA_QUALITY", None, "PERCENT", ">=90", "UNKNOWN", "Нет итоговой оценки качества данных.", "udl.quality.overall_score", "LOW"))
    elif data_quality_score >= 90:
        kpis.append(_item("Data quality score", "DATA_QUALITY", data_quality_score, "PERCENT", ">=90", "GOOD", "Качество данных высокое.", "udl.quality.overall_score", "HIGH"))
    elif data_quality_score >= 70:
        kpis.append(_item("Data quality score", "DATA_QUALITY", data_quality_score, "PERCENT", ">=90", "WARNING", "Качество данных требует осторожности.", "udl.quality.overall_score", "MEDIUM"))
    else:
        kpis.append(_item("Data quality score", "DATA_QUALITY", data_quality_score, "PERCENT", ">=90", "CRITICAL", "Качество данных недостаточно для уверенных выводов.", "udl.quality.overall_score", "LOW"))

    if trust_score is None:
        kpis.append(_item("Trust score", "DATA_QUALITY", None, "PERCENT", ">=85", "UNKNOWN", "Нет итоговой оценки trust score.", "udl.trust.overall_trust", "LOW"))
    elif trust_score >= 85:
        kpis.append(_item("Trust score", "DATA_QUALITY", trust_score, "PERCENT", ">=85", "GOOD", "Уровень доверия к данным высокий.", "udl.trust.overall_trust", "HIGH"))
    elif trust_score >= 60:
        kpis.append(_item("Trust score", "DATA_QUALITY", trust_score, "PERCENT", ">=85", "WARNING", "Уровень доверия к данным средний.", "udl.trust.overall_trust", "MEDIUM"))
    else:
        kpis.append(_item("Trust score", "DATA_QUALITY", trust_score, "PERCENT", ">=85", "CRITICAL", "Уровень доверия к данным низкий.", "udl.trust.overall_trust", "LOW"))

    if str(unified_costs.get("status") or "") in ("DETAIL_REQUIRED", "unavailable", "UNAVAILABLE", "RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "API_ENDPOINT_ERROR", "ERROR"):
        kpis.append(_item("SKU cost coverage", "SKU", None, "PERCENT", ">=95%", "UNKNOWN", "Покрытие себестоимости недоступно до получения детальных финансовых строк.", "udl.costs.status", "LOW"))
    elif sku_cost_coverage is None:
        kpis.append(_item("SKU cost coverage", "SKU", None, "PERCENT", ">=95%", "UNKNOWN", "Нет данных по покрытию себестоимости.", "business_metrics.cost_coverage_percent", "LOW"))
    elif sku_cost_coverage >= 95:
        kpis.append(_item("SKU cost coverage", "SKU", sku_cost_coverage, "PERCENT", ">=95%", "GOOD", "Покрытие себестоимости высокое.", "cost_coverage_percent", "HIGH"))
    elif sku_cost_coverage >= 80:
        kpis.append(_item("SKU cost coverage", "SKU", sku_cost_coverage, "PERCENT", ">=95%", "WARNING", "Покрытие себестоимости неполное.", "cost_coverage_percent", "MEDIUM"))
    else:
        kpis.append(_item("SKU cost coverage", "SKU", sku_cost_coverage, "PERCENT", ">=95%", "CRITICAL", "Покрытие себестоимости слишком низкое.", "cost_coverage_percent", "LOW"))

    if payment_status in ("MATCHED", "PAID", "OK"):
        kpis.append(_item("Payment reconciliation", "CASHFLOW", payment_status, "STATUS", "MATCHED / PAID", "GOOD", "Сверка выплат выглядит корректной.", "payments.status", "HIGH"))
    elif payment_status in ("EXPECTED_TIMING_DIFFERENCE", "EXPECTED_NEXT_PERIOD"):
        kpis.append(_item("Payment reconciliation", "CASHFLOW", payment_status, "STATUS", "MATCHED / PAID", "NORMAL", "Есть ожидаемый временной лаг между продажами и выплатами.", "payments.status", "MEDIUM"))
    elif payment_status in ("DIFF", "NEEDS_REVIEW"):
        kpis.append(_item("Payment reconciliation", "CASHFLOW", payment_status, "STATUS", "MATCHED / PAID", "WARNING", "Сверка выплат требует ручной проверки.", "payments.status", "MEDIUM"))
    elif payment_status == "ERROR":
        kpis.append(_item("Payment reconciliation", "CASHFLOW", payment_status, "STATUS", "MATCHED / PAID", "CRITICAL", "Сверка выплат завершилась ошибкой.", "payments.status", "LOW"))
    else:
        kpis.append(_item("Payment reconciliation", "CASHFLOW", payment_status, "STATUS", "MATCHED / PAID", "UNKNOWN", "Статус сверки выплат неизвестен.", "payments.status", "LOW"))

    if not official_available and operational_available:
        kpis.append(_item("Official vs operational model", "FINANCE", "operational_without_official", "STATUS", "official available", "WARNING", "Операционная модель доступна без подтверждённой официальной прибыли.", "official_available=false and operational_available=true", "HIGH"))
    elif official_available:
        kpis.append(_item("Official vs operational model", "FINANCE", "aligned", "STATUS", "official available", "GOOD", "Официальный финансовый результат доступен.", "official_available=true", "HIGH"))
    else:
        kpis.append(_item("Official vs operational model", "FINANCE", "unknown", "STATUS", "official available", "UNKNOWN", "Недостаточно данных для сравнения моделей.", "insufficient data", "LOW"))

    summary = _status_counts(kpis)
    if summary["total_kpis"] <= 0:
        status = "INSUFFICIENT_DATA"
    elif summary["critical_count"] > 0 or summary["warning_count"] > 0 or summary["unknown_count"] > 0:
        status = "PARTIAL"
    else:
        status = "OK"

    return {
        "status": status,
        "period": dict(period_snapshot or {}),
        "data_confidence": data_confidence,
        "kpis": kpis,
        "summary": summary,
        "warnings": _dedup_texts(warnings),
    }


def _group_title(group_name):
    mapping = {
        "FINANCE": "Finance KPIs",
        "SALES": "Sales KPIs",
        "ADS": "Ads KPIs",
        "SKU": "SKU KPIs",
        "DATA_QUALITY": "Data Quality KPIs",
        "CASHFLOW": "Cashflow KPIs",
    }
    return mapping.get(str(group_name or ""), str(group_name or "Other KPIs"))


def _format_value(value, unit):
    if value is None:
        return "n/a"
    if unit == "RUB":
        return f"{float(value):.2f}"
    if unit == "PERCENT":
        return f"{float(value):.1f}%"
    return str(value)


def kpi_engine_text(snapshot):
    snapshot = dict(snapshot or {})
    period = dict(snapshot.get("period") or {})
    start_date = period.get("start_date") or period.get("start") or "-"
    end_date = period.get("end_date") or period.get("end") or "-"
    summary = dict(snapshot.get("summary") or {})
    kpis = list(snapshot.get("kpis") or [])
    warnings = list(snapshot.get("warnings") or [])

    grouped = {}
    for item in kpis:
        group = str(item.get("group") or "UNKNOWN")
        grouped.setdefault(group, []).append(item)

    lines = [
        "KPI ENGINE",
        "",
        f"Period: {start_date}..{end_date}",
        f'Overall status: {summary.get("overall_status") or "UNKNOWN"}',
        "",
        "Summary:",
        f'GOOD: {int(summary.get("good_count") or 0)}',
        f'NORMAL: {int(summary.get("normal_count") or 0)}',
        f'WARNING: {int(summary.get("warning_count") or 0)}',
        f'CRITICAL: {int(summary.get("critical_count") or 0)}',
        f'UNKNOWN: {int(summary.get("unknown_count") or 0)}',
    ]

    for group_name in ("FINANCE", "ADS", "DATA_QUALITY", "SKU", "CASHFLOW", "SALES"):
        items = grouped.get(group_name) or []
        if not items and group_name == "SALES":
            continue
        lines.extend(["", f"{_group_title(group_name)}:"])
        if items:
            for index, item in enumerate(items, 1):
                lines.append(
                    f'{index}. {item.get("name")}: {_format_value(item.get("value"), item.get("unit"))} | '
                    f'status {item.get("status")} | {item.get("message")}'
                )
        else:
            lines.append("1. no KPI items")

    lines.extend(["", "Warnings:"])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    return "\n".join(lines)
