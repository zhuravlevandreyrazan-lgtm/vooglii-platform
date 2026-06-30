"""Pure read-only Decision Engine helpers.

This module builds a rule-based estimate layer from already prepared
snapshots. It must not call APIs, read/write DB, mutate cache, or change
financial formulas.
"""

from wb_agent.formatting import money

DECISION_ENGINE_ALLOWED_STATUS = ("OK", "PARTIAL", "INSUFFICIENT_DATA")
DECISION_ENGINE_ALLOWED_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")
DECISION_ENGINE_ALLOWED_SCENARIO_CATEGORIES = (
    "ADS",
    "PRICE",
    "SKU",
    "COST",
    "CASHFLOW",
    "DATA_QUALITY",
    "FINANCE",
)
DECISION_ENGINE_ALLOWED_ESTIMATE_TYPES = (
    "ROUGH_ESTIMATE",
    "DIRECTIONAL",
    "INSUFFICIENT_DATA",
)
DECISION_ENGINE_ALLOWED_RISKS = ("LOW", "MEDIUM", "HIGH")

__all__ = [
    "DECISION_ENGINE_ALLOWED_STATUS",
    "DECISION_ENGINE_ALLOWED_CONFIDENCE",
    "DECISION_ENGINE_ALLOWED_SCENARIO_CATEGORIES",
    "DECISION_ENGINE_ALLOWED_ESTIMATE_TYPES",
    "DECISION_ENGINE_ALLOWED_RISKS",
    "build_decision_snapshot",
    "decision_engine_text",
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


def _text_list(items):
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


def _derive_confidence(trust_score, fallback=None):
    fallback_text = str(fallback or "").strip().upper()
    if fallback_text in DECISION_ENGINE_ALLOWED_CONFIDENCE:
        return fallback_text
    score = _int_or_none(trust_score)
    if score is None:
        return "LOW"
    if score >= 85:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def _confidence_text(value):
    return {
        "HIGH": "высокая",
        "MEDIUM": "средняя",
        "LOW": "низкая",
    }.get(str(value or "").upper(), "низкая")


def _risk_text(value):
    return {
        "LOW": "низкий",
        "MEDIUM": "средний",
        "HIGH": "высокий",
    }.get(str(value or "").upper(), "средний")


def _status_text(value):
    return {
        "OK": "можно использовать для управленческих оценок",
        "PARTIAL": "частично доступно для управленческих оценок",
        "INSUFFICIENT_DATA": "недостаточно данных для точных решений",
    }.get(str(value or "").upper(), "недостаточно данных для точных решений")


def _scenario(
    scenario_id,
    title,
    category,
    estimate_type,
    current_value,
    target_value,
    expected_effect,
    expected_profit_effect,
    risk,
    confidence,
    basis,
    action,
):
    return {
        "id": str(scenario_id),
        "title": str(title),
        "category": str(category),
        "estimate_type": str(estimate_type),
        "current_value": current_value,
        "target_value": target_value,
        "expected_effect": str(expected_effect),
        "expected_profit_effect": _float_or_none(expected_profit_effect),
        "risk": str(risk),
        "confidence": str(confidence),
        "basis": str(basis),
        "action": str(action),
    }


def _period_payload(period_snapshot):
    period_snapshot = dict(period_snapshot or {})
    start_date = str(period_snapshot.get("start_date") or "")
    end_date = str(period_snapshot.get("end_date") or "")
    return {
        "start_date": start_date or None,
        "end_date": end_date or None,
        "display_name": str(
            period_snapshot.get("display_name")
            or (f"{start_date}..{end_date}" if start_date and end_date else "Unknown")
        ),
        "period_type": str(period_snapshot.get("period_type") or "UNKNOWN"),
    }


def build_decision_snapshot(
    period_snapshot=None,
    unified_data_snapshot=None,
    business_metrics_snapshot=None,
    kpi_snapshot=None,
    cfo_insights_snapshot=None,
    sku_registry_snapshot=None,
):
    period_snapshot = dict(period_snapshot or {})
    unified_data_snapshot = dict(unified_data_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    kpi_snapshot = dict(kpi_snapshot or {})
    cfo_insights_snapshot = dict(cfo_insights_snapshot or {})
    sku_registry_snapshot = dict(sku_registry_snapshot or {})

    period = _period_payload(period_snapshot)
    udl_sales = dict(unified_data_snapshot.get("sales") or {})
    udl_ads = dict(unified_data_snapshot.get("advertising") or {})
    udl_payments = dict(unified_data_snapshot.get("payments") or {})
    udl_costs = dict(unified_data_snapshot.get("costs") or {})
    udl_quality = dict(unified_data_snapshot.get("quality") or {})
    udl_trust = dict(unified_data_snapshot.get("trust") or {})
    udl_finance = dict(unified_data_snapshot.get("finance") or {})

    trust_score = _int_or_none(
        udl_trust.get("overall_trust")
        if "overall_trust" in udl_trust
        else business_metrics_snapshot.get("trust_score")
    )
    data_confidence = _derive_confidence(trust_score, fallback=kpi_snapshot.get("data_confidence"))
    quality_status = str(udl_quality.get("overall_status") or "UNKNOWN")
    official_available = bool(business_metrics_snapshot.get("official_available"))
    operational_available = bool(business_metrics_snapshot.get("operational_available"))
    finance_status = str(
        business_metrics_snapshot.get("official_status")
        or udl_finance.get("status")
        or "UNAVAILABLE"
    )
    payment_status = str(udl_payments.get("status") or "UNKNOWN")
    cost_status = str(udl_costs.get("status") or "UNKNOWN")
    cost_coverage = _float_or_none(udl_costs.get("coverage_percent"))

    scenarios = []
    risks = []
    warnings = []

    if not official_available:
        scenarios.append(
            _scenario(
                "finance_api_unavailable",
                "Do not finalize month-close profit decisions until Finance API is restored",
                "FINANCE",
                "INSUFFICIENT_DATA",
                finance_status,
                "official financial profit available",
                "Exact month-close profit decisions remain blocked until the official finance layer is restored.",
                None,
                "HIGH",
                "HIGH" if finance_status in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR") else "MEDIUM",
                f"business_metrics.official_available={official_available}; finance_status={finance_status}",
                "Не принимать решения по закрытию месяца до восстановления Finance API.",
            )
        )
        risks.append("Official financial profit is unavailable for precise month-close decisions.")

    if operational_available and not official_available:
        scenarios.append(
            _scenario(
                "operational_only_mode",
                "Use operational profit only for operational decisions",
                "FINANCE",
                "DIRECTIONAL",
                "operational_only",
                "official + operational clearly separated",
                "Operational estimates can support daily decisions, but not official month-close conclusions.",
                None,
                "HIGH",
                "HIGH",
                "business_metrics.operational_available=true and official_available=false",
                "Использовать operational только для оперативных решений, а не для закрытия месяца.",
            )
        )
        risks.append("Operational estimate must not be treated as official financial profit.")

    revenue = _float_or_none(udl_sales.get("revenue"))
    ads_spend = _float_or_none(udl_ads.get("total_spend"))
    if revenue is not None and revenue > 0 and ads_spend is not None:
        ads_share = round((ads_spend / revenue) * 100.0, 1)
        if ads_share > 15.0:
            scenarios.append(
                _scenario(
                    "ads_reduce_drr",
                    "Check whether advertising load can be reduced",
                    "ADS",
                    "ROUGH_ESTIMATE",
                    ads_share,
                    "8-15%",
                    "Potential savings of about 5-10% of current ad spend without assuming exact demand elasticity.",
                    round(ads_spend * 0.05, 2),
                    "MEDIUM",
                    "MEDIUM" if data_confidence in ("HIGH", "MEDIUM") else "LOW",
                    f"ads_share={ads_share}%; advertising.total_spend={ads_spend}; sales.revenue={revenue}",
                    "Проверить снижение рекламной нагрузки и отключение слабых кампаний без резкого массового урезания.",
                )
            )
            risks.append("Advertising share is above the preferred working range.")
        elif ads_share >= 8.0:
            scenarios.append(
                _scenario(
                    "ads_working_range",
                    "Advertising is inside the working range",
                    "ADS",
                    "DIRECTIONAL",
                    ads_share,
                    "8-15%",
                    "No immediate budget cut is indicated without SKU-level review.",
                    None,
                    "LOW",
                    "MEDIUM",
                    f"ads_share={ads_share}%",
                    "Не снижать резко бюджет без SKU-разбора и проверки слабых кампаний.",
                )
            )
        else:
            scenarios.append(
                _scenario(
                    "ads_scale_carefully",
                    "There may be room for careful advertising scale-up",
                    "ADS",
                    "DIRECTIONAL",
                    ads_share,
                    "8-15%",
                    "Low advertising share may allow careful scaling, but exact upside remains an estimate.",
                    None,
                    "MEDIUM",
                    "LOW" if data_confidence == "LOW" else "MEDIUM",
                    f"ads_share={ads_share}%",
                    "Тестировать аккуратное масштабирование рекламы только по сильным SKU и без резкого роста затрат.",
                )
            )
    else:
        warnings.append("Advertising share scenario skipped because revenue or ad spend is unavailable.")

    if trust_score is not None and trust_score >= 85 and quality_status == "HIGH":
        scenarios.append(
            _scenario(
                "data_quality_ready",
                "Data quality is strong enough for management scenarios",
                "DATA_QUALITY",
                "DIRECTIONAL",
                trust_score,
                ">=85 and HIGH",
                "Prepared snapshots are suitable for management estimates with normal caution.",
                None,
                "LOW",
                "HIGH",
                f"trust_score={trust_score}; quality.overall_status={quality_status}",
                "Можно использовать Decision Engine для управленческих сценариев, сохраняя пометку estimate.",
            )
        )
    else:
        current_quality = f'trust={trust_score if trust_score is not None else "-"}, quality={quality_status}'
        scenarios.append(
            _scenario(
                "data_quality_first",
                "Improve data quality before high-confidence management decisions",
                "DATA_QUALITY",
                "INSUFFICIENT_DATA" if data_confidence == "LOW" else "DIRECTIONAL",
                current_quality,
                "trust>=85 and HIGH",
                "Low trust or mixed quality reduces confidence in any management estimate.",
                None,
                "HIGH" if data_confidence == "LOW" else "MEDIUM",
                "HIGH" if trust_score is not None else "MEDIUM",
                f"trust_score={trust_score}; quality.overall_status={quality_status}",
                "Сначала улучшить качество данных, затем принимать чувствительные решения по прибыли и масштабу.",
            )
        )
        risks.append("Data quality should be improved before high-confidence management decisions.")

    if cost_status in ("DETAIL_REQUIRED", "unavailable", "UNAVAILABLE", "RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "API_ENDPOINT_ERROR", "ERROR", "UNKNOWN"):
        scenarios.append(
            _scenario(
                "sku_cost_coverage_unavailable",
                "Close SKU cost coverage before SKU-level profit decisions",
                "COST",
                "INSUFFICIENT_DATA",
                cost_status,
                "coverage >=95%",
                "SKU-level profit actions remain unsafe until cost coverage is restored.",
                None,
                "HIGH",
                "HIGH",
                f"udl.costs.status={cost_status}",
                "Закрыть справочник себестоимости перед SKU-решениями.",
            )
        )
        risks.append("SKU-level profit decisions are unsafe while cost coverage is unavailable.")
    elif cost_coverage is not None and cost_coverage < 95.0:
        scenarios.append(
            _scenario(
                "sku_cost_coverage_partial",
                "SKU profit decisions may be distorted by incomplete cost coverage",
                "COST",
                "DIRECTIONAL",
                cost_coverage,
                ">=95%",
                "Incomplete cost coverage can bias SKU-level profit ranking and prioritization.",
                None,
                "MEDIUM",
                "MEDIUM",
                f"udl.costs.coverage_percent={cost_coverage}",
                "Перед SKU-решениями довести покрытие себестоимости хотя бы до 95%.",
            )
        )
        risks.append("Incomplete cost coverage can distort SKU-level profit decisions.")

    if payment_status in ("EXPECTED_TIMING_DIFFERENCE", "EXPECTED_NEXT_PERIOD"):
        scenarios.append(
            _scenario(
                "payment_timing_lag",
                "Account for payout timing lag",
                "CASHFLOW",
                "DIRECTIONAL",
                payment_status,
                "timing aligned or explained",
                "The gap between sales and received payouts is likely timing-related, not automatically a loss.",
                None,
                "LOW",
                "HIGH",
                f"payments.status={payment_status}",
                "Не считать разницу между продажами и выплатами потерей денег без учета временного лага.",
            )
        )

    top_actions = []
    for preferred_category in ("FINANCE", "ADS", "DATA_QUALITY", "COST", "CASHFLOW"):
        for scenario in scenarios:
            if scenario.get("category") != preferred_category:
                continue
            action_text = str(scenario.get("action") or "").strip()
            if not action_text or action_text in top_actions:
                continue
            top_actions.append(action_text)
            break
        if len(top_actions) >= 3:
            break

    warnings.extend(_text_list(unified_data_snapshot.get("warnings")))
    warnings.extend(_text_list(cfo_insights_snapshot.get("warnings")))
    warnings.append("Decision Engine is a rule-based estimate layer and does not perform WB actions.")
    warnings = _text_list(warnings)
    risks = _text_list(risks)

    if data_confidence == "LOW" and (not official_available or quality_status != "HIGH"):
        status = "INSUFFICIENT_DATA"
    elif any(item.get("estimate_type") == "INSUFFICIENT_DATA" for item in scenarios):
        status = "PARTIAL"
    else:
        status = "OK"

    return {
        "status": status,
        "period": period,
        "data_confidence": data_confidence,
        "scenarios": scenarios,
        "top_actions": top_actions[:3],
        "risks": risks,
        "warnings": warnings,
    }


def _decision_summary(snapshot, scenarios):
    snapshot = dict(snapshot or {})
    scenario_ids = {str(item.get("id") or "") for item in list(scenarios or [])}
    can_do = []
    cannot_do = []

    if "ads_reduce_drr" in scenario_ids or "ads_working_range" in scenario_ids or "ads_scale_carefully" in scenario_ids:
        can_do.append("управлять рекламой")
    if "data_quality_ready" in scenario_ids or "data_quality_first" in scenario_ids:
        can_do.append("анализировать данные")
    if "payment_timing_lag" in scenario_ids:
        can_do.append("контролировать временной лаг выплат")

    if "finance_api_unavailable" in scenario_ids or str(snapshot.get("status") or "") == "INSUFFICIENT_DATA":
        cannot_do.append("закрывать месяц")
    if "sku_cost_coverage_unavailable" in scenario_ids or "sku_cost_coverage_partial" in scenario_ids:
        cannot_do.append("принимать SKU-profit решения без детализации себестоимости")

    decision_status = "Точные решения по закрытию месяца пока заблокированы Finance API."
    if "finance_api_unavailable" not in scenario_ids:
        decision_status = "Часть управленческих решений доступна, но требует аккуратной интерпретации."

    return {
        "decision_status": decision_status,
        "can_do": can_do or ["анализировать данные"],
        "cannot_do": cannot_do or ["принимать решения без проверки качества данных"],
    }


def _scenario_title_ru(item):
    mapping = {
        "finance_api_unavailable": "Точные решения по закрытию месяца пока недоступны",
        "operational_only_mode": "Операционную прибыль использовать только для оперативных решений",
        "ads_reduce_drr": "Проверить снижение рекламной нагрузки",
        "ads_working_range": "Реклама находится в рабочем диапазоне",
        "ads_scale_carefully": "Есть потенциал аккуратного масштабирования рекламы",
        "data_quality_ready": "Качество данных подходит для управленческих сценариев",
        "data_quality_first": "Сначала улучшить качество данных",
        "sku_cost_coverage_unavailable": "Сначала закрыть себестоимость для SKU-решений",
        "sku_cost_coverage_partial": "Неполная себестоимость искажает SKU-решения",
        "payment_timing_lag": "Учитывать временной лаг выплат",
    }
    return mapping.get(str((item or {}).get("id") or ""), str((item or {}).get("title") or "-"))


def _scenario_effect_ru(item):
    mapping = {
        "finance_api_unavailable": "До восстановления Finance API нельзя безопасно подтверждать итоговую прибыль месяца.",
        "operational_only_mode": "Операционная оценка подходит для ежедневного контроля, но не заменяет официальный финансовый результат.",
        "ads_reduce_drr": "Потенциальная экономия может составить около 5-10% текущих рекламных расходов.",
        "ads_working_range": "Резкое снижение рекламного бюджета сейчас не выглядит обязательным без SKU-разбора.",
        "ads_scale_carefully": "Низкая рекламная доля оставляет пространство для осторожного роста рекламы по сильным SKU.",
        "data_quality_ready": "Текущие данные можно использовать для управленческих оценок с нормальной осторожностью.",
        "data_quality_first": "Смешанное качество данных снижает уверенность в управленческих решениях.",
        "sku_cost_coverage_unavailable": "SKU-решения по прибыли остаются ненадежными, пока себестоимость не закрыта.",
        "sku_cost_coverage_partial": "Неполное покрытие себестоимости может искажать ранжирование SKU по прибыли.",
        "payment_timing_lag": "Разница между продажами и выплатами может объясняться календарным лагом, а не потерей денег.",
    }
    return mapping.get(str((item or {}).get("id") or ""), str((item or {}).get("expected_effect") or "-"))


def _scenario_basis_ru(item):
    item = dict(item or {})
    scenario_id = str(item.get("id") or "")
    current_value = item.get("current_value")
    if scenario_id.startswith("ads_") and current_value not in (None, ""):
        return f"Основание: рекламная доля {current_value}%."
    if scenario_id.startswith("data_quality_"):
        return f"Основание: уверенность в данных {_confidence_text(item.get('confidence'))}."
    if scenario_id.startswith("sku_cost_coverage") and current_value not in (None, ""):
        if isinstance(current_value, (int, float)):
            return f"Основание: покрытие себестоимости {current_value}%."
        return "Основание: себестоимость по SKU пока не подтверждена."
    if scenario_id == "payment_timing_lag":
        return "Основание: в выплатах обнаружен ожидаемый временной лаг."
    if scenario_id in ("finance_api_unavailable", "operational_only_mode"):
        return "Основание: официальный финансовый контур сейчас недоступен."
    return ""


def _risk_item_ru(text):
    raw = str(text or "").strip()
    lowered = raw.lower()
    if "official financial profit is unavailable" in lowered:
        return "Точная официальная прибыль недоступна для закрытия месяца."
    if "operational estimate must not be treated as official financial profit" in lowered:
        return "Операционную оценку нельзя считать официальной прибылью."
    if "advertising share is above the preferred working range" in lowered:
        return "Рекламная доля выше комфортного рабочего диапазона."
    if "data quality should be improved" in lowered:
        return "Качество данных нужно улучшить перед чувствительными решениями."
    if "sku-level profit decisions are unsafe while cost coverage is unavailable" in lowered:
        return "SKU-решения по прибыли небезопасны без подтвержденной себестоимости."
    if "incomplete cost coverage can distort sku-level profit decisions" in lowered:
        return "Неполная себестоимость может искажать выводы по SKU-прибыли."
    return raw


def _warning_lines(snapshot, scenarios, warnings):
    scenario_ids = {str(item.get("id") or "") for item in list(scenarios or [])}
    result = []
    if "finance_api_unavailable" in scenario_ids:
        result.append("Finance API временно недоступен. Точные решения по закрытию месяца лучше отложить.")
    if "operational_only_mode" in scenario_ids:
        result.append("Операционная оценка не является официальной прибылью.")
    result.append("Decision Engine показывает оценочные сценарии и не выполняет действий в WB.")

    for item in list(warnings or []):
        text = str(item or "").strip()
        lowered = text.lower()
        if not text:
            continue
        if "cooldown_source" in lowered:
            continue
        if "rule-based estimate layer" in lowered:
            continue
        if "operational profit is not official financial profit" in lowered:
            continue
        if "finance api cooldown active" in lowered:
            continue
        if "decision engine is a rule-based estimate layer" in lowered:
            continue
        if "advertising share scenario skipped" in lowered:
            result.append("Для части рекламных сценариев не хватило данных по выручке или расходам.")

    return _text_list(result)[:4]


def decision_engine_text(snapshot):
    snapshot = dict(snapshot or {})
    period = dict(snapshot.get("period") or {})
    scenarios = list(snapshot.get("scenarios") or [])
    top_actions = list(snapshot.get("top_actions") or [])
    risks = list(snapshot.get("risks") or [])
    warnings = list(snapshot.get("warnings") or [])
    summary = _decision_summary(snapshot, scenarios)
    warning_lines = _warning_lines(snapshot, scenarios, warnings)

    period_text = str(
        period.get("display_name")
        or (
            f'{period.get("start_date")}..{period.get("end_date")}'
            if period.get("start_date") and period.get("end_date")
            else "Unknown"
        )
    )

    lines = [
        "DECISION ENGINE",
        "",
        f"Период: {period_text}",
        f'Статус: {_status_text(snapshot.get("status"))}',
        f'Уверенность: {_confidence_text(snapshot.get("data_confidence"))}',
        "",
        "EXECUTIVE SUMMARY",
        f'Статус решений: {summary.get("decision_status") or "-"}',
        "",
        "Что можно делать:",
    ]
    for idx, item in enumerate(summary.get("can_do") or [], 1):
        lines.append(f"{idx}. {item}")

    lines.extend([
        "",
        "Что нельзя делать:",
    ])
    for idx, item in enumerate(summary.get("cannot_do") or [], 1):
        lines.append(f"{idx}. {item}")

    lines.extend([
        "",
        "Что сделать сейчас:",
    ])
    if top_actions:
        for idx, item in enumerate(top_actions[:3], 1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. Нет действий с достаточной уверенностью.")

    lines.extend(["", "Управленческие сценарии:"])
    if scenarios:
        for idx, item in enumerate(scenarios, 1):
            profit_effect = item.get("expected_profit_effect")
            profit_text = money(profit_effect) if profit_effect is not None else "оценка без точной суммы"
            basis_text = _scenario_basis_ru(item)
            lines.extend([
                f'{idx}. {_scenario_title_ru(item)}',
                f'Ожидаемый эффект: {_scenario_effect_ru(item)}',
                f'Оценка эффекта на прибыль: {profit_text}',
                f'Риск: {_risk_text(item.get("risk"))} | Уверенность: {_confidence_text(item.get("confidence"))}',
            ])
            if basis_text:
                lines.append(basis_text)
            lines.extend([
                f'Действие: {item.get("action") or "-"}',
                "",
            ])
        if lines[-1] == "":
            lines.pop()
    else:
        lines.append("1. Нет сценариев.")

    lines.extend(["", "Риски:"])
    if risks:
        for idx, item in enumerate(risks, 1):
            lines.append(f"{idx}. {_risk_item_ru(item)}")
    else:
        lines.append("1. Явных рисков не выявлено.")

    if warning_lines:
        lines.extend(["", "Предупреждения:"])
        for idx, item in enumerate(warning_lines, 1):
            lines.append(f"{idx}. {item}")

    lines.extend([
        "",
        "Заключение:",
        "Decision Engine не выполняет действий в кабинете WB. Все сценарии являются оценкой для принятия решений.",
    ])
    return "\n".join(lines)
