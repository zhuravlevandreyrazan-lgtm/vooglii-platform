"""Pure read-only Advisor v2 helpers.

This module aggregates existing snapshots into a recommendation layer.
It must not call APIs, read/write DB, mutate cache, or change formulas.
"""

ADVISOR_V2_ALLOWED_STATUS = ("OK", "PARTIAL", "INSUFFICIENT_DATA")
ADVISOR_V2_ALLOWED_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")
ADVISOR_V2_ALLOWED_PRIORITY = ("HIGH", "MEDIUM", "LOW")
ADVISOR_V2_ALLOWED_CATEGORY = ("FINANCE", "ADS", "SKU", "DATA", "CASHFLOW", "STRATEGY")
ADVISOR_V2_ALLOWED_SOURCE = ("KPI", "CFO", "DECISION", "UDL", "BUSINESS_METRICS")

__all__ = [
    "ADVISOR_V2_ALLOWED_STATUS",
    "ADVISOR_V2_ALLOWED_CONFIDENCE",
    "ADVISOR_V2_ALLOWED_PRIORITY",
    "ADVISOR_V2_ALLOWED_CATEGORY",
    "ADVISOR_V2_ALLOWED_SOURCE",
    "build_advisor_v2_snapshot",
    "advisor_v2_text",
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


def _period_payload(period_snapshot):
    period_snapshot = dict(period_snapshot or {})
    start_date = str(period_snapshot.get("start_date") or "")
    end_date = str(period_snapshot.get("end_date") or "")
    display_name = str(
        period_snapshot.get("display_name")
        or (f"{start_date}..{end_date}" if start_date and end_date else "Unknown")
    )
    return {
        "start_date": start_date or None,
        "end_date": end_date or None,
        "display_name": display_name,
        "period_type": str(period_snapshot.get("period_type") or "UNKNOWN"),
    }


def _derive_confidence(trust_score, *fallbacks):
    for value in fallbacks:
        text = str(value or "").strip().upper()
        if text in ADVISOR_V2_ALLOWED_CONFIDENCE:
            return text
    score = _int_or_none(trust_score)
    if score is None:
        return "LOW"
    if score >= 85:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def _recommendation(priority, category, title, message, action, basis, confidence, source):
    return {
        "priority": str(priority),
        "category": str(category),
        "title": str(title),
        "message": str(message),
        "action": str(action),
        "basis": str(basis),
        "confidence": str(confidence),
        "source": str(source),
    }


def _finance_unavailable(status_text, official_profit_available):
    normalized = str(status_text or "").upper()
    return (not official_profit_available) or normalized in (
        "RATE_LIMIT",
        "FORBIDDEN",
        "UNAUTHORIZED",
        "UNAVAILABLE",
        "DETAIL_REQUIRED",
        "API_ENDPOINT_ERROR",
        "ERROR",
    )


def _action_group_for_item(text):
    lowered = str(text or "").lower()
    if not lowered:
        return "optional"
    if "finance api" in lowered or "закрыт" in lowered or "месяц" in lowered:
        return "critical"
    if "cashflow" in lowered or "выплат" in lowered or "реклам" in lowered or "sku" in lowered:
        return "recommended"
    return "optional"


def _sanitize_decision_action(action_text):
    text = str(action_text or "").strip()
    lowered = text.lower()
    if not text:
        return ""
    if "finance api" in lowered and "месяц" in lowered:
        return "Дождаться Finance API перед закрытием месяца."
    if "sku" in lowered and ("себесто" in lowered or "profit" in lowered):
        return "Подтвердить себестоимость перед решениями по SKU."
    if "реклам" in lowered:
        return "Разобрать рекламу по SKU и кампаниям перед изменением бюджета."
    if "выплат" in lowered or "лаг" in lowered:
        return "Проверить временной лаг выплат перед выводами по денежному потоку."
    if "данн" in lowered:
        return "Использовать текущие данные для ежедневного контроля бизнеса."
    return text[:160]


def _append_action(bucket, text):
    clean = str(text or "").strip()
    if clean:
        bucket.append(clean)


def _rating_sales(unified_data_snapshot):
    sales = dict((unified_data_snapshot or {}).get("sales") or {})
    revenue = _float_or_none(sales.get("revenue"))
    if revenue is not None and revenue > 0:
        return "доступны"
    return "данных недостаточно"


def _rating_ads(ads_share, ads_status):
    if ads_share is None:
        return "вывод по рекламе ограничен"
    if ads_share > 15.0:
        return "доля выше рабочего диапазона"
    if ads_share < 8.0:
        return "доля ниже рабочего диапазона"
    if str(ads_status or "").upper() == "HIGH":
        return "в рабочем диапазоне"
    return "под контролем, но требует проверки"


def _rating_finance(finance_unavailable):
    if finance_unavailable:
        return "ожидают Finance API"
    return "доступны для закрытия периода"


def _rating_data(quality_status, trust_score):
    if str(quality_status or "").upper() == "HIGH" and (trust_score or 0) >= 85:
        return "качество высокое"
    if str(quality_status or "").upper() == "LOW":
        return "качество требует внимания"
    return "качество приемлемое"


def _rating_costs(cost_status, cost_coverage):
    normalized = str(cost_status or "").upper()
    if normalized in ("DETAIL_REQUIRED", "UNKNOWN") or cost_coverage is None:
        return "требует детализации для официальной прибыли"
    if normalized in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "API_ENDPOINT_ERROR", "ERROR"):
        return "временно недоступна детализация"
    if cost_coverage < 95.0:
        return "покрытие неполное"
    return "достаточна для управленческого контроля"


def _ads_message(ads_share):
    if ads_share is None:
        return "Рекламный вывод недоступен без данных по рекламе."
    if ads_share > 15.0:
        return f"Рекламная доля около {ads_share:.1f}% от оборота — это выше целевого диапазона. Нужен разбор кампаний и SKU."
    if ads_share < 8.0:
        return f"Рекламная доля около {ads_share:.1f}% от оборота — она ниже рабочего диапазона. Можно рассмотреть аккуратное масштабирование, если продажи стабильны."
    return f"Рекламная доля около {ads_share:.1f}% от оборота — это рабочий диапазон. Резко снижать бюджет сейчас не рекомендуется."


def _business_summary(finance_unavailable, quality_status, trust_score):
    if finance_unavailable:
        if str(quality_status or "").upper() == "HIGH" and (trust_score or 0) >= 85:
            return "Бизнес можно контролировать по операционным данным, но финансовое закрытие временно недоступно."
        return "Операционный контроль возможен частично, но финансовое закрытие временно недоступно."
    return "Бизнес можно контролировать по текущим данным, а закрытие периода не выглядит заблокированным."


def build_advisor_v2_snapshot(
    period_snapshot=None,
    unified_data_snapshot=None,
    business_metrics_snapshot=None,
    financial_engine_snapshot=None,
    kpi_snapshot=None,
    cfo_insights_snapshot=None,
    decision_snapshot=None,
    sku_registry_snapshot=None,
):
    period_snapshot = dict(period_snapshot or {})
    unified_data_snapshot = dict(unified_data_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    kpi_snapshot = dict(kpi_snapshot or {})
    cfo_insights_snapshot = dict(cfo_insights_snapshot or {})
    decision_snapshot = dict(decision_snapshot or {})
    sku_registry_snapshot = dict(sku_registry_snapshot or {})

    period = _period_payload(period_snapshot)
    udl_quality = dict(unified_data_snapshot.get("quality") or {})
    udl_trust = dict(unified_data_snapshot.get("trust") or {})
    udl_ads = dict(unified_data_snapshot.get("advertising") or {})
    udl_payments = dict(unified_data_snapshot.get("payments") or {})
    udl_costs = dict(unified_data_snapshot.get("costs") or {})

    financial_status = str(
        financial_engine_snapshot.get("status")
        or business_metrics_snapshot.get("official_status")
        or "UNAVAILABLE"
    )
    official_profit_available = bool(business_metrics_snapshot.get("official_available"))
    operational_estimate_available = bool(business_metrics_snapshot.get("operational_available"))
    trust_score = _int_or_none(
        udl_trust.get("overall_trust")
        if "overall_trust" in udl_trust
        else business_metrics_snapshot.get("trust_score")
    )
    quality_status = str(udl_quality.get("overall_status") or "")
    data_confidence = _derive_confidence(
        trust_score,
        decision_snapshot.get("data_confidence"),
        kpi_snapshot.get("data_confidence"),
        cfo_insights_snapshot.get("data_confidence"),
    )
    finance_unavailable = _finance_unavailable(financial_status, official_profit_available)

    ads_share = _float_or_none(udl_ads.get("share_of_revenue_percent"))
    if ads_share is None:
        total_spend = _float_or_none(udl_ads.get("total_spend"))
        revenue = _float_or_none((unified_data_snapshot.get("sales") or {}).get("revenue"))
        if total_spend not in (None, 0) and revenue not in (None, 0):
            ads_share = round((total_spend / revenue) * 100.0, 1)

    recommendations = []
    do_now = []
    do_later = []
    do_not_do = []
    risks = []
    warnings = []
    critical_actions = []
    recommended_actions = []
    optional_actions = []

    main_recommendation = _recommendation(
        "MEDIUM",
        "STRATEGY",
        "Сохранять управленческий контроль без резких действий",
        "Текущий слой рекомендаций помогает расставить приоритеты, но не выполняет действий в кабинете WB.",
        "Использовать рекомендации как управленческую опору для ежедневного контроля.",
        "KPI, CFO, Decision, UDL",
        data_confidence,
        "DECISION",
    )

    if finance_unavailable:
        main_recommendation = _recommendation(
            "HIGH",
            "FINANCE",
            "Не закрывать месяц до восстановления Finance API",
            "Финансовое закрытие периода лучше отложить, пока официальная финансовая картина временно недоступна.",
            "Дождаться Finance API перед закрытием месяца.",
            "Статус финансового слоя указывает на временную недоступность официальной прибыли.",
            "HIGH",
            "BUSINESS_METRICS",
        )
        _append_action(do_now, "Дождаться Finance API перед закрытием месяца.")
        _append_action(critical_actions, "Дождаться Finance API перед закрытием месяца.")

    if operational_estimate_available and not official_profit_available:
        _append_action(do_not_do, "Не использовать операционную оценку как официальную чистую прибыль.")

    ads_text = _ads_message(ads_share)
    if ads_share is not None:
        if ads_share > 15.0:
            recommendations.append(
                _recommendation(
                    "HIGH",
                    "ADS",
                    "Реклама требует разбора",
                    ads_text,
                    "Разобрать кампании и SKU перед изменением рекламного бюджета.",
                    f"Рекламная доля около {ads_share:.1f}% от оборота.",
                    "MEDIUM" if data_confidence != "LOW" else "LOW",
                    "UDL",
                )
            )
            _append_action(do_now, "Разобрать кампании и SKU перед изменением рекламного бюджета.")
            _append_action(recommended_actions, "Разобрать кампании и SKU перед изменением рекламного бюджета.")
        elif ads_share < 8.0:
            recommendations.append(
                _recommendation(
                    "LOW",
                    "ADS",
                    "Можно рассмотреть осторожное масштабирование рекламы",
                    ads_text,
                    "Подготовить осторожные тесты масштабирования по сильным SKU.",
                    f"Рекламная доля около {ads_share:.1f}% от оборота.",
                    "MEDIUM",
                    "UDL",
                )
            )
            _append_action(do_later, "Подготовить осторожные тесты масштабирования по сильным SKU.")
            _append_action(optional_actions, "Подготовить осторожные тесты масштабирования по сильным SKU.")
        else:
            recommendations.append(
                _recommendation(
                    "MEDIUM",
                    "ADS",
                    "Рекламу лучше не сокращать резко",
                    ads_text,
                    "Проверить эффективность рекламы по SKU и точечно оптимизировать слабые кампании.",
                    f"Рекламная доля около {ads_share:.1f}% от оборота.",
                    "MEDIUM",
                    "UDL",
                )
            )
            _append_action(do_now, "Проверить эффективность рекламы по SKU и точечно оптимизировать слабые кампании.")
            _append_action(recommended_actions, "Проверить эффективность рекламы по SKU и точечно оптимизировать слабые кампании.")
    else:
        recommendations.append(
            _recommendation(
                "LOW",
                "ADS",
                "По рекламе не хватает данных для уверенного вывода",
                ads_text,
                "Вернуться к рекламному выводу после обновления данных.",
                "Данных по рекламной доле недостаточно.",
                "LOW",
                "UDL",
            )
        )

    if quality_status.upper() == "HIGH" and (trust_score or 0) >= 85:
        recommendations.append(
            _recommendation(
                "LOW",
                "DATA",
                "Операционные данные подходят для ежедневного контроля",
                "Качество данных выглядит достаточно сильным для ежедневных управленческих решений.",
                "Продолжать ежедневный контроль рекламы, продаж и выплат по текущим данным.",
                f"Trust score {trust_score}.",
                "HIGH",
                "UDL",
            )
        )
        _append_action(do_later, "Продолжать ежедневный контроль рекламы, продаж и выплат по текущим данным.")
        _append_action(optional_actions, "Продолжать ежедневный контроль рекламы, продаж и выплат по текущим данным.")
    else:
        recommendations.append(
            _recommendation(
                "MEDIUM",
                "DATA",
                "К данным стоит относиться осторожно",
                "Часть управленческих выводов лучше перепроверять, пока качество данных не стало устойчиво высоким.",
                "Проверять чувствительные выводы по данным вручную перед важными решениями.",
                f"Текущая уверенность в данных: {data_confidence}.",
                data_confidence,
                "UDL",
            )
        )
        _append_action(do_later, "Проверять чувствительные выводы по данным вручную перед важными решениями.")

    registry_status = str(sku_registry_snapshot.get("registry_status") or "").upper()
    cost_status = str(udl_costs.get("status") or "").upper()
    cost_coverage = _float_or_none(
        udl_costs.get("coverage_percent")
        if "coverage_percent" in udl_costs
        else sku_registry_snapshot.get("coverage_percent")
    )
    if registry_status in ("PARTIAL", "MISSING", "UNAVAILABLE") or cost_status in (
        "DETAIL_REQUIRED",
        "UNKNOWN",
        "RATE_LIMIT",
        "FORBIDDEN",
        "UNAUTHORIZED",
        "UNAVAILABLE",
        "API_ENDPOINT_ERROR",
        "ERROR",
    ) or (cost_coverage is not None and cost_coverage < 95.0):
        risks.append("SKU-решения по прибыли пока небезопасны без полного покрытия себестоимости.")
        _append_action(do_not_do, "Не принимать SKU-profit решения без детализации себестоимости.")
        _append_action(recommended_actions, "Подтвердить себестоимость перед решениями по SKU.")

    payment_status = str(udl_payments.get("status") or "")
    if payment_status == "EXPECTED_TIMING_DIFFERENCE":
        recommendations.append(
            _recommendation(
                "MEDIUM",
                "CASHFLOW",
                "Разницу между продажами и выплатами важно читать аккуратно",
                "Текущий разрыв между продажами и выплатами может объясняться временным лагом, а не потерей денег.",
                "Проверить временной лаг выплат перед выводами по денежному потоку.",
                "Есть признаки ожидаемого временного лага между продажами и выплатами.",
                "HIGH",
                "KPI",
            )
        )
        _append_action(do_now, "Проверить временной лаг выплат перед выводами по денежному потоку.")
        _append_action(recommended_actions, "Проверить временной лаг выплат перед выводами по денежному потоку.")

    for action_text in list(decision_snapshot.get("top_actions") or [])[:3]:
        action = _sanitize_decision_action(action_text)
        if not action:
            continue
        _append_action(do_now, action)
        bucket = _action_group_for_item(action)
        if bucket == "critical":
            _append_action(critical_actions, action)
        elif bucket == "recommended":
            _append_action(recommended_actions, action)
        else:
            _append_action(optional_actions, action)

    if main_recommendation.get("action"):
        action = str(main_recommendation.get("action") or "").strip()
        if action and action not in do_now:
            _append_action(do_now, action)
            bucket = _action_group_for_item(action)
            if bucket == "critical":
                _append_action(critical_actions, action)
            elif bucket == "recommended":
                _append_action(recommended_actions, action)
            else:
                _append_action(optional_actions, action)

    do_now = _text_list(do_now)[:6]
    do_later = _text_list(do_later)[:6]
    do_not_do = _text_list(do_not_do)[:6]
    risks = _text_list(risks)[:6]
    critical_actions = _text_list(critical_actions)[:3]
    recommended_actions = _text_list(recommended_actions)[:4]
    optional_actions = _text_list(optional_actions)[:4]

    business_state = {
        "sales": _rating_sales(unified_data_snapshot),
        "ads": _rating_ads(ads_share, udl_ads.get("status")),
        "finance": _rating_finance(finance_unavailable),
        "data": _rating_data(quality_status, trust_score),
        "costs": _rating_costs(cost_status, cost_coverage),
        "summary": _business_summary(finance_unavailable, quality_status, trust_score),
        "ads_message": ads_text,
    }
    action_groups = {
        "critical": critical_actions,
        "recommended": recommended_actions,
        "optional": optional_actions,
    }

    warnings.extend(_text_list(unified_data_snapshot.get("warnings")))
    warnings.extend(_text_list(cfo_insights_snapshot.get("warnings")))
    warnings.extend(_text_list(decision_snapshot.get("warnings")))
    warnings.append("Advisor v2 не выполняет действий в кабинете WB. Это слой рекомендаций.")
    warnings = _text_list(warnings)

    if data_confidence == "LOW" and finance_unavailable:
        status = "INSUFFICIENT_DATA"
    elif finance_unavailable or risks:
        status = "PARTIAL"
    else:
        status = "OK"

    return {
        "status": status,
        "period": period,
        "data_confidence": data_confidence,
        "main_recommendation": main_recommendation,
        "recommendations": recommendations,
        "do_now": do_now,
        "do_later": do_later,
        "do_not_do": do_not_do,
        "risks": risks,
        "warnings": warnings,
        "business_state": business_state,
        "action_groups": action_groups,
    }


def _lines_for_bucket(lines, title, items, empty_text):
    lines.append(title)
    if items:
        for idx, item in enumerate(items, 1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append(f"1. {empty_text}")


def advisor_v2_text(snapshot):
    snapshot = dict(snapshot or {})
    period = dict(snapshot.get("period") or {})
    business_state = dict(snapshot.get("business_state") or {})
    action_groups = dict(snapshot.get("action_groups") or {})
    main_recommendation = dict(snapshot.get("main_recommendation") or {})
    do_not_do = list(snapshot.get("do_not_do") or [])
    risks = list(snapshot.get("risks") or [])

    period_text = str(
        period.get("display_name")
        or (
            f'{period.get("start_date")}..{period.get("end_date")}'
            if period.get("start_date") and period.get("end_date")
            else "Unknown"
        )
    )

    lines = [
        "ADVISOR v2",
        "",
        f"Период: {period_text}",
        "",
        "ОБЩЕЕ СОСТОЯНИЕ БИЗНЕСА",
        f'Продажи: {business_state.get("sales") or "данных недостаточно"}',
        f'Реклама: {business_state.get("ads") or "данных недостаточно"}',
        f'Финансы: {business_state.get("finance") or "данных недостаточно"}',
        f'Данные: {business_state.get("data") or "данных недостаточно"}',
        f'Себестоимость: {business_state.get("costs") or "данных недостаточно"}',
        f'Итог: {business_state.get("summary") or "данных недостаточно для уверенного вывода."}',
        "",
        "ГЛАВНАЯ РЕКОМЕНДАЦИЯ",
        str(main_recommendation.get("title") or "-"),
        str(main_recommendation.get("message") or "-"),
    ]

    ads_message = str(business_state.get("ads_message") or "").strip()
    if ads_message:
        lines.extend(["", ads_message])

    lines.extend(["", "ЧТО СДЕЛАТЬ СЕЙЧАС"])
    _lines_for_bucket(
        lines,
        "Критично:",
        list(action_groups.get("critical") or []),
        "Критичных действий сейчас не требуется.",
    )
    lines.append("")
    _lines_for_bucket(
        lines,
        "Желательно:",
        list(action_groups.get("recommended") or []),
        "Срочных управленческих действий сейчас не требуется.",
    )
    lines.append("")
    _lines_for_bucket(
        lines,
        "Можно сделать:",
        list(action_groups.get("optional") or []),
        "Можно вернуться к этим задачам после следующего обновления данных.",
    )

    lines.extend(["", "ЧЕГО НЕ ДЕЛАТЬ"])
    if do_not_do:
        for idx, item in enumerate(do_not_do, 1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. Не делать резких изменений без проверки деталей.")

    lines.extend(["", "КЛЮЧЕВЫЕ РИСКИ"])
    if risks:
        for idx, item in enumerate(risks, 1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. Критичные риски сейчас явно не выражены.")

    lines.extend([
        "",
        "ОСНОВАНИЕ",
        "- KPI Engine",
        "- CFO Insights",
        "- Decision Engine",
        "- UDL",
        "",
        "Важно:",
        "Advisor v2 не выполняет действий в кабинете WB. Это слой рекомендаций.",
    ])
    return "\n".join(lines)
