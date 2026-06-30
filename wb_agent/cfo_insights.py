"""Pure read-only CFO insight helpers.

This module must not call APIs, read/write DB, mutate cache, or recalculate
financial formulas. It only transforms prepared snapshot dicts into simple
rule-based business insights.
"""

CFO_INSIGHTS_ALLOWED_STATUS = ("OK", "PARTIAL", "INSUFFICIENT_DATA")
CFO_INSIGHTS_ALLOWED_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")
CFO_INSIGHTS_ALLOWED_TYPES = ("PROFIT", "SALES", "ADS", "FINANCE", "SKU", "DATA_QUALITY", "CASHFLOW")
CFO_INSIGHTS_ALLOWED_SEVERITY = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")

__all__ = [
    "CFO_INSIGHTS_ALLOWED_STATUS",
    "CFO_INSIGHTS_ALLOWED_CONFIDENCE",
    "CFO_INSIGHTS_ALLOWED_TYPES",
    "CFO_INSIGHTS_ALLOWED_SEVERITY",
    "build_cfo_insights_snapshot",
    "cfo_insights_text",
]


def _list_text(value):
    result = []
    for item in list(value or []):
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


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


def _is_may_2026_period(period_snapshot):
    period_snapshot = dict(period_snapshot or {})
    return (
        str(period_snapshot.get("start_date") or "") == "2026-05-01"
        and str(period_snapshot.get("end_date") or "") == "2026-05-31"
    )


def _append_entry(target, entry_type, severity, title, message, basis, confidence):
    target.append({
        "type": str(entry_type),
        "severity": str(severity),
        "title": str(title),
        "message": str(message),
        "basis": str(basis),
        "confidence": str(confidence),
    })


def _derive_data_confidence(trust_score):
    score = _int_or_none(trust_score)
    if score is None:
        return "LOW"
    if score >= 85:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def build_cfo_insights_snapshot(
    period_snapshot=None,
    unified_data_snapshot=None,
    business_metrics_snapshot=None,
    financial_engine_snapshot=None,
    ads_snapshot=None,
    sku_registry_snapshot=None,
):
    period_snapshot = dict(period_snapshot or {})
    unified_data_snapshot = dict(unified_data_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    ads_snapshot = dict(ads_snapshot or {})
    sku_registry_snapshot = dict(sku_registry_snapshot or {})

    insights = []
    risks = []
    opportunities = []
    actions = []
    warnings = []

    trust = dict(unified_data_snapshot.get("trust") or {})
    quality = dict(unified_data_snapshot.get("quality") or {})
    finance = dict(unified_data_snapshot.get("finance") or {})
    advertising = dict(unified_data_snapshot.get("advertising") or {})
    costs = dict(unified_data_snapshot.get("costs") or {})

    trust_score = trust.get("overall_trust")
    data_confidence = _derive_data_confidence(trust_score)
    official_profit_available = bool(business_metrics_snapshot.get("official_available"))
    operational_estimate_available = bool(business_metrics_snapshot.get("operational_available"))
    legacy_estimate_available = bool(
        business_metrics_snapshot.get("legacy_estimate_available")
        or financial_engine_snapshot.get("legacy_estimate_available")
    )
    legacy_gold_validation_status = str(financial_engine_snapshot.get("legacy_gold_validation_status") or "NOT_APPLICABLE")

    finance_status = str(financial_engine_snapshot.get("status") or business_metrics_snapshot.get("official_status") or finance.get("status") or "UNAVAILABLE")
    ads_health_status = str(business_metrics_snapshot.get("advertising_health") or advertising.get("status") or ads_snapshot.get("status") or "UNKNOWN")
    cost_coverage_percent = _float_or_none(
        business_metrics_snapshot.get("cost_coverage_percent")
        or financial_engine_snapshot.get("cost_coverage_percent")
        or costs.get("coverage_percent")
    )
    quality_score = _float_or_none(business_metrics_snapshot.get("data_quality_score") or quality.get("overall_score"))

    if finance_status == "LEGACY_FALLBACK":
        _append_entry(
            insights,
            "FINANCE",
            "MEDIUM",
            "Legacy fallback mode",
            "Финансовые строки получены через legacy finance API. Расчёт пригоден для сверки, но не заменяет новый Finance API.",
            "financial_engine.status=LEGACY_FALLBACK",
            "MEDIUM",
        )
        actions.append("Использовать legacy fallback только для сверки и не закрывать период как final official mode.")
        warnings.append("legacy fallback mode")
        if legacy_gold_validation_status == "MATCHED_LEGACY":
            _append_entry(
                insights,
                "FINANCE",
                "INFO",
                "Legacy fallback validated",
                "Legacy finance fallback совпал с майским эталоном, но новый Finance API всё ещё недоступен.",
                "financial_engine.legacy_gold_validation_status=MATCHED_LEGACY",
                "HIGH",
            )
        elif legacy_gold_validation_status == "NEEDS_REVIEW":
            _append_entry(
                risks,
                "FINANCE",
                "HIGH",
                "Legacy fallback requires review",
                "Legacy finance fallback требует проверки перед использованием.",
                "financial_engine.legacy_gold_validation_status=NEEDS_REVIEW",
                "HIGH",
            )
    elif finance_status in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "API_ENDPOINT_ERROR"):
        _append_entry(
            insights,
            "FINANCE",
            "HIGH",
            "Официальная финансовая прибыль не подтверждена",
            "WB Finance API временно недоступен, поэтому итоговая чистая прибыль месяца пока не подтверждена.",
            f"financial_engine.status={finance_status}",
            "HIGH",
        )
        actions.append("Дождаться восстановления доступа к WB Finance API.")
    elif finance_status == "DETAIL_REQUIRED":
        _append_entry(
            insights,
            "FINANCE",
            "HIGH",
            "Нужна детализация финансового отчёта WB",
            "Для окончательного расчёта нужна детализация финансового отчёта WB.",
            "financial_engine.status=DETAIL_REQUIRED",
            "HIGH",
        )
        actions.append("После восстановления доступа обновить финансовый отчёт и подтвердить итоговую прибыль.")

    if operational_estimate_available and not official_profit_available:
        _append_entry(
            risks,
            "PROFIT",
            "HIGH",
            "Операционная оценка не подходит для закрытия месяца",
            "Операционная оценка доступна, но не заменяет официальный финансовый результат.",
            "business_metrics.operational_available=true and official_available=false",
            "HIGH",
        )

    if ads_health_status == "HIGH":
        _append_entry(
            insights,
            "ADS",
            "INFO",
            "Рекламные данные доступны",
            "Рекламные данные получены и пригодны для управленческой аналитики.",
            f"ads_health={ads_health_status}",
            "HIGH",
        )
    elif ads_health_status in ("MEDIUM", "PARTIAL"):
        _append_entry(
            risks,
            "ADS",
            "MEDIUM",
            "Рекламные данные частично ограничены",
            "Связка рекламы с SKU и финансовыми результатами может быть неполной.",
            f"ads_health={ads_health_status}",
            "MEDIUM",
        )
    elif ads_health_status not in ("UNKNOWN", "UNAVAILABLE"):
        _append_entry(
            risks,
            "ADS",
            "HIGH",
            "Рекламные данные требуют перепроверки",
            "Низкое качество рекламных данных ограничивает уверенность в управленческих выводах.",
            f"ads_health={ads_health_status}",
            "MEDIUM",
        )

    cost_status = str(costs.get("status") or finance_status or "UNKNOWN")
    if cost_status in ("DETAIL_REQUIRED", "unavailable", "UNAVAILABLE", "RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "API_ENDPOINT_ERROR", "ERROR"):
        _append_entry(
            risks,
            "FINANCE",
            "HIGH",
            "Себестоимость для итогового результата не подтверждена",
            "Для окончательного расчёта нужна детализация финансового отчёта WB.",
            f"cost_status={cost_status}",
            "HIGH",
        )
    elif cost_coverage_percent is not None and cost_coverage_percent >= 95:
        _append_entry(
            opportunities,
            "FINANCE",
            "INFO",
            "Покрытие себестоимости высокое",
            "Покрытие себестоимости уже достаточно для уверенной управленческой интерпретации.",
            f"cost_coverage_percent={cost_coverage_percent:.1f}",
            "HIGH",
        )

    if quality_score is not None and quality_score >= 90:
        _append_entry(
            insights,
            "DATA_QUALITY",
            "INFO",
            "Качество данных высокое",
            "Текущий набор данных подходит для оперативного управления.",
            f"data_quality_score={quality_score:.1f}",
            "HIGH",
        )
    elif quality_score is not None:
        severity = "MEDIUM" if quality_score >= 70 else "HIGH"
        confidence = "MEDIUM" if quality_score >= 70 else "LOW"
        _append_entry(
            risks,
            "DATA_QUALITY",
            severity,
            "Качество данных требует внимания",
            "Часть выводов лучше перепроверить перед окончательными решениями.",
            f"data_quality_score={quality_score:.1f}",
            confidence,
        )

    if data_confidence == "HIGH":
        _append_entry(
            opportunities,
            "DATA_QUALITY",
            "INFO",
            "Уверенность в данных высокая",
            "Операционные данные пригодны для ежедневного управления.",
            f"trust_score={trust_score}",
            "HIGH",
        )
    elif data_confidence == "MEDIUM":
        _append_entry(
            risks,
            "DATA_QUALITY",
            "LOW",
            "Уверенность в данных средняя",
            "Управленческие выводы стоит перепроверять смежными отчётами.",
            f"trust_score={trust_score}",
            "MEDIUM",
        )
    else:
        _append_entry(
            risks,
            "DATA_QUALITY",
            "MEDIUM",
            "Уверенность в данных низкая",
            "Текущие выводы лучше использовать как предварительную оценку.",
            f"trust_score={trust_score}",
            "LOW",
        )

    registry_status = str(sku_registry_snapshot.get("registry_status") or "UNKNOWN")
    registry_coverage = _float_or_none(sku_registry_snapshot.get("coverage_percent"))
    if registry_coverage is not None and registry_coverage >= 95:
        _append_entry(
            opportunities,
            "SKU",
            "INFO",
            "Справочник SKU покрыт почти полностью",
            "Справочник SKU и себестоимости покрывает почти весь периодный набор товаров.",
            f"sku_registry.coverage_percent={registry_coverage:.1f}",
            "HIGH",
        )
    elif registry_status in ("PARTIAL", "EMPTY"):
        _append_entry(
            risks,
            "SKU",
            "MEDIUM",
            "Справочник SKU покрыт не полностью",
            "Часть SKU пока не имеет полного покрытия по reference себестоимости.",
            f"sku_registry.status={registry_status}",
            "MEDIUM",
        )

    if _is_may_2026_period(period_snapshot) and not official_profit_available:
        warnings.append("Майский эталон подтверждён, но текущий автоматический расчёт требует доступа к Finance API.")
    if legacy_estimate_available:
        warnings.append("legacy fallback mode")

    warnings.extend(_list_text(unified_data_snapshot.get("warnings")))
    warnings.extend(_list_text(business_metrics_snapshot.get("notes")))
    warnings = _dedup_business_texts(warnings)

    if not insights and not risks and not opportunities and not actions:
        status = "INSUFFICIENT_DATA"
        warnings = _dedup_business_texts(warnings + ["INSUFFICIENT_DATA"])
    elif official_profit_available and data_confidence == "HIGH":
        status = "OK"
    else:
        status = "PARTIAL"

    return {
        "status": status,
        "period": dict(period_snapshot or {}),
        "data_confidence": data_confidence,
        "official_profit_available": official_profit_available,
        "operational_estimate_available": operational_estimate_available,
        "insights": insights,
        "risks": risks,
        "opportunities": opportunities,
        "actions": actions,
        "warnings": warnings,
    }


def _business_warning_text(text):
    normalized = str(text or "").strip()
    lower = normalized.lower()
    if not normalized:
        return ""
    if "gold standard" in lower or ("may 2026" in lower and "finance api" in lower):
        return "Майский эталон подтверждён, но текущий автоматический расчёт требует доступа к Finance API."
    if "cost trust unavailable" in lower or "detailed finance rows" in lower or "detail_required" in lower:
        return "Для окончательного расчёта нужна детализация финансового отчёта WB."
    if "operational profit is not official financial profit" in lower:
        return "Операционная оценка не подходит для закрытия месяца."
    if "finance api" in lower and ("unavailable" in lower or "rate_limit" in lower or "недоступ" in lower):
        return "WB Finance API временно недоступен."
    if "official profit unavailable" in lower or "official financial profit" in lower:
        return "Официальная финансовая прибыль пока не рассчитана."
    if "insufficient_data" in lower:
        return "Недостаточно данных для уверенного финансового вывода."
    return normalized


def _sanitize_entry(item):
    item = dict(item or {})
    title = str(item.get("title") or "").strip()
    message = str(item.get("message") or "").strip()
    lower_title = title.lower()
    lower_message = message.lower()

    if "official financial profit" in lower_message or "official profit" in lower_message:
        message = "Официальная чистая прибыль пока не подтверждена."
    if "official financial profit" in lower_title or "official profit" in lower_title:
        title = "Официальная прибыль пока не подтверждена"
    if "operational" in lower_message and "official" in lower_message:
        message = "Операционная оценка не подходит для закрытия месяца."
    if "operational" in lower_title and "official" in lower_title:
        title = "Операционная оценка не подходит для закрытия месяца"
    if "detailed finance rows" in lower_message or "detail_required" in lower_message:
        message = "Для окончательного расчёта нужна детализация финансового отчёта WB."
    if "detailed finance rows" in lower_title or "detail_required" in lower_title:
        title = "Нужна детализация финансового отчёта WB"
    if "cost trust" in lower_message:
        message = "Себестоимость для итогового результата пока не подтверждена."
    if any(term in lower_message for term in ("regression", "reference", "runtime")):
        message = _business_warning_text(message)
    if any(term in lower_title for term in ("regression", "reference", "runtime")):
        title = "Требуется подтверждение через Finance API"

    item["title"] = title or "Финансовый вывод"
    item["message"] = message or "Требуется дополнительная проверка."
    return item


def _dedup_business_texts(items):
    result = []
    seen = set()
    for item in items:
        text = _business_warning_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _confidence_label(value):
    mapping = {
        "HIGH": "высокая",
        "MEDIUM": "средняя",
        "LOW": "низкая",
    }
    return mapping.get(str(value or "").upper(), "низкая")


def _confidence_comment(snapshot):
    if not bool(snapshot.get("official_profit_available")):
        return "Операционные данные пригодны для ежедневного управления. Финансовое закрытие периода пока не подтверждено."
    if str(snapshot.get("data_confidence") or "") == "HIGH":
        return "Операционные данные пригодны для ежедневного управления."
    if str(snapshot.get("data_confidence") or "") == "MEDIUM":
        return "Данные подходят для оперативного управления, но требуют выборочной перепроверки."
    return "Данные лучше использовать как предварительную оценку до дополнительного подтверждения."


def _report_readiness_snapshot(snapshot):
    finance_ready = bool(snapshot.get("official_profit_available"))
    data_confidence = str(snapshot.get("data_confidence") or "LOW")
    risks = list(snapshot.get("risks") or [])

    if finance_ready:
        readiness_percent = 100
    elif data_confidence == "HIGH":
        readiness_percent = 80
    elif data_confidence == "MEDIUM":
        readiness_percent = 75
    else:
        readiness_percent = 60

    if any("себестоимость" in str(item.get("title") or "").lower() for item in risks):
        readiness_percent -= 5
    if any("finance api" in str(item.get("message") or "").lower() for item in risks + list(snapshot.get("insights") or [])):
        readiness_percent -= 5

    readiness_percent = max(40, min(100, readiness_percent))

    reasons = []
    if not finance_ready:
        reasons.append("WB Finance API временно недоступен.")
        reasons.append("Официальная чистая прибыль ждёт подтверждения через Finance API.")
    if data_confidence == "LOW":
        reasons.append("Качество данных пока недостаточно для уверенного закрытия периода.")
    return {
        "percent": readiness_percent,
        "reasons": _dedup_business_texts(reasons),
    }


def _executive_summary_lines(snapshot):
    finance_unavailable = not bool(snapshot.get("official_profit_available"))
    insights = list(snapshot.get("insights") or [])
    lines = [
        "EXECUTIVE SUMMARY",
        "",
        "Статус месяца:",
    ]
    if finance_unavailable:
        lines.append("Финансовый результат временно не подтверждён.")
    else:
        lines.append("Финансовый результат подтверждён.")

    lines.extend(["", "Причина:"])
    if finance_unavailable:
        lines.append("WB Finance API временно недоступен.")
    else:
        lines.append("Ключевые финансовые данные подтверждены.")

    lines.extend(["", "Что уже известно:"])
    if bool(snapshot.get("operational_estimate_available")):
        lines.append("1. Продажи получены.")
    if any(str(item.get("type") or "") == "ADS" and str(item.get("severity") or "") == "INFO" for item in insights):
        lines.append("2. Реклама получена.")
    if str(snapshot.get("data_confidence") or "") == "HIGH":
        lines.append("3. Качество данных высокое.")
    elif str(snapshot.get("data_confidence") or "") == "MEDIUM":
        lines.append("3. Качество данных достаточно для оперативной оценки.")
    else:
        lines.append("3. Доступна предварительная операционная оценка.")

    lines.extend(["", "Что ожидает подтверждения:"])
    if finance_unavailable:
        lines.append("1. Комиссия WB.")
        lines.append("2. Полная детализация удержаний.")
        lines.append("3. Официальная чистая прибыль.")
    else:
        lines.append("1. Критичных неподтверждённых блоков не осталось.")

    lines.extend(["", "Следующее действие:"])
    if finance_unavailable:
        lines.append("Повторить проверку после восстановления Finance API.")
    else:
        lines.append("Использовать отчёт как основу для управленческих решений.")
    return lines


def _entries_section_lines(title, entries):
    entries = [_sanitize_entry(item) for item in list(entries or [])]
    if not entries:
        return []
    lines = [title]
    for index, item in enumerate(entries, 1):
        lines.append(f'{index}. {item.get("title")}: {item.get("message")}')
    return lines


def _risk_section_lines(entries):
    entries = [_sanitize_entry(item) for item in list(entries or [])]
    high_items = [item for item in entries if str(item.get("severity") or "") in ("HIGH", "CRITICAL")]
    medium_items = [item for item in entries if str(item.get("severity") or "") in ("MEDIUM", "LOW")]
    info_items = [item for item in entries if str(item.get("severity") or "") == "INFO"]

    if not (high_items or medium_items or info_items):
        return []

    lines = ["Ключевые риски:"]
    if high_items:
        lines.extend(["", "Высокий приоритет"])
        for index, item in enumerate(high_items, 1):
            lines.append(f'{index}. {item.get("title")}: {item.get("message")}')
    if medium_items:
        lines.extend(["", "Средний приоритет"])
        for index, item in enumerate(medium_items, 1):
            lines.append(f'{index}. {item.get("title")}: {item.get("message")}')
    if info_items:
        lines.extend(["", "Информационно"])
        for index, item in enumerate(info_items, 1):
            lines.append(f'{index}. {item.get("title")}: {item.get("message")}')
    return lines


def _readiness_lines(snapshot):
    readiness = _report_readiness_snapshot(snapshot)
    lines = [
        "ГОТОВНОСТЬ ФИНАНСОВОГО ОТЧЁТА",
        "",
        f'Готовность финансового отчёта: {readiness.get("percent")}%',
    ]
    reasons = list(readiness.get("reasons") or [])
    if reasons and int(readiness.get("percent") or 0) < 100:
        lines.extend(["", "Причина неполной готовности:"])
        for index, reason in enumerate(reasons, 1):
            lines.append(f"{index}. {reason}")
    return lines


def _recommended_actions_lines(snapshot):
    actions = []
    period = dict(snapshot.get("period") or {})
    start_date = period.get("start_date") or period.get("start") or "-"
    end_date = period.get("end_date") or period.get("end") or "-"

    if not bool(snapshot.get("official_profit_available")):
        actions.append("Не закрывать месяц по операционной оценке.")
        actions.append("Дождаться восстановления доступа к WB Finance API.")
        actions.append("После восстановления обновить финансовый отчёт и подтвердить итоговую прибыль.")
    else:
        actions.extend(_dedup_business_texts(snapshot.get("actions") or []))

    command_lines = [
        "/finance api status",
        f"/financial engine {start_date} {end_date}",
        f"/cfo insights {start_date} {end_date}",
    ]

    lines = []
    if actions:
        lines.append("Рекомендуемые действия:")
        for index, item in enumerate(actions, 1):
            lines.append(f"{index}. {item}")
    lines.extend(["", "Команды для проверки:"])
    for item in command_lines:
        lines.append(f"- {item}")
    return lines


def _cfo_conclusion_lines(snapshot):
    if bool(snapshot.get("official_profit_available")):
        conclusion = (
            "Финансовый результат подтверждён. Данные можно использовать для закрытия периода "
            "и для управленческих решений."
        )
    else:
        conclusion = (
            "Бизнес можно контролировать по операционным данным, но закрывать месяц по ним нельзя. "
            "Финансовое закрытие месяца рекомендуется выполнить после восстановления доступа к "
            "WB Finance API и подтверждения официальной финансовой прибыли."
        )
    return [
        "ЗАКЛЮЧЕНИЕ CFO",
        "",
        conclusion,
    ]


def _warnings_lines(snapshot):
    warnings = _dedup_business_texts(snapshot.get("warnings") or [])
    risks_text = " ".join(
        f'{item.get("title", "")} {item.get("message", "")}'.lower()
        for item in [_sanitize_entry(item) for item in list(snapshot.get("risks") or [])]
    )
    insights_text = " ".join(
        f'{item.get("title", "")} {item.get("message", "")}'.lower()
        for item in [_sanitize_entry(item) for item in list(snapshot.get("insights") or [])]
    )

    filtered = []
    for item in warnings:
        lowered = item.lower()
        if lowered in risks_text or lowered in insights_text:
            continue
        filtered.append(item)

    if not filtered:
        return []
    lines = ["Предупреждения:"]
    for index, item in enumerate(filtered, 1):
        lines.append(f"{index}. {item}")
    return lines


def cfo_insights_text(snapshot):
    snapshot = dict(snapshot or {})
    period = dict(snapshot.get("period") or {})
    start_date = period.get("start_date") or period.get("start") or "-"
    end_date = period.get("end_date") or period.get("end") or "-"

    sections = [
        [
            "CFO INSIGHTS",
            "",
            f"Период: {start_date}..{end_date}",
            f'Статус: {snapshot.get("status") or "INSUFFICIENT_DATA"}',
            f'Уверенность в данных: {_confidence_label(snapshot.get("data_confidence"))}',
            f"Комментарий: {_confidence_comment(snapshot)}",
        ],
        _executive_summary_lines(snapshot),
        _readiness_lines(snapshot),
        _entries_section_lines("Основные выводы:", snapshot.get("insights") or []),
        _risk_section_lines(snapshot.get("risks") or []),
        _entries_section_lines("Возможности:", snapshot.get("opportunities") or []),
        _recommended_actions_lines(snapshot),
        _cfo_conclusion_lines(snapshot),
        _warnings_lines(snapshot),
    ]

    lines = []
    for section in sections:
        clean_section = [str(item) for item in list(section or []) if str(item).strip()]
        if not clean_section:
            continue
        if lines:
            lines.append("")
        lines.extend(clean_section)
    return "\n".join(lines)
