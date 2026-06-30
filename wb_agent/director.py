"""Pure read-only AI Director helpers.

This module builds an executive summary layer from prepared snapshots.
It must not call APIs, read/write DB, mutate cache, or change formulas.
"""

DIRECTOR_ALLOWED_STATUS = ("OK", "PARTIAL", "INSUFFICIENT_DATA")
DIRECTOR_ALLOWED_BUSINESS_HEALTH = ("GOOD", "NORMAL", "WARNING", "CRITICAL", "UNKNOWN")
DIRECTOR_ALLOWED_CONFIDENCE = ("HIGH", "MEDIUM", "LOW")
DIRECTOR_ALLOWED_BLOCK_STATE = ("GOOD", "NORMAL", "WARNING", "BLOCKED", "UNKNOWN")

__all__ = [
    "DIRECTOR_ALLOWED_STATUS",
    "DIRECTOR_ALLOWED_BUSINESS_HEALTH",
    "DIRECTOR_ALLOWED_CONFIDENCE",
    "DIRECTOR_ALLOWED_BLOCK_STATE",
    "build_director_snapshot",
    "director_text",
]


def _int_or_none(value):
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _float_or_none(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
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
    return {
        "start_date": start_date or None,
        "end_date": end_date or None,
        "display_name": str(
            period_snapshot.get("display_name")
            or (f"{start_date}..{end_date}" if start_date and end_date else "Unknown")
        ),
        "period_type": str(period_snapshot.get("period_type") or "UNKNOWN"),
    }


def _sanitize_text(text):
    result = str(text or "").strip()
    replacements = {
        "RATE_LIMIT": "временно недоступно",
        "DETAIL_REQUIRED": "требуется детализация",
        "INSUFFICIENT_DATA": "недостаточно данных",
        "runtime": "текущий контур",
        "operational estimate": "операционная оценка",
        "estimate only": "предварительная оценка",
        "official profit": "официальная прибыль",
        "official financial profit": "официальная прибыль",
    }
    for source, target in replacements.items():
        result = result.replace(source, target)
        result = result.replace(source.lower(), target)
    return result


def _item(title, message, confidence, source):
    return {
        "title": str(title),
        "message": str(message),
        "confidence": str(confidence),
        "source": str(source),
    }


def _summary_status_to_health(overall_status):
    mapping = {
        "GOOD": "GOOD",
        "NORMAL": "NORMAL",
        "WARNING": "WARNING",
        "CRITICAL": "CRITICAL",
        "UNKNOWN": "UNKNOWN",
    }
    return mapping.get(str(overall_status or "").upper(), "UNKNOWN")


def _finance_blocked(financial_status, official_profit_available):
    normalized = str(financial_status or "").upper()
    if normalized == "LEGACY_FALLBACK":
        return False
    return (not official_profit_available) or normalized in (
        "RATE_LIMIT",
        "FORBIDDEN",
        "UNAVAILABLE",
        "API_ENDPOINT_ERROR",
        "ERROR",
    )


def _sales_state(unified_data_snapshot):
    revenue = _float_or_none(((unified_data_snapshot.get("sales") or {}).get("revenue")))
    return "GOOD" if revenue and revenue > 0 else "UNKNOWN"


def _ads_state(unified_data_snapshot, business_metrics_snapshot):
    advertising = dict(unified_data_snapshot.get("advertising") or {})
    ads_status = str(advertising.get("status") or business_metrics_snapshot.get("advertising_health") or "").upper()
    spend = _float_or_none(advertising.get("total_spend"))
    if ads_status == "HIGH" and spend is not None:
        return "GOOD"
    if ads_status in ("MEDIUM", "NORMAL"):
        return "NORMAL"
    if ads_status:
        return "WARNING"
    return "UNKNOWN"


def _data_quality_state(unified_data_snapshot, business_metrics_snapshot):
    quality = dict(unified_data_snapshot.get("quality") or {})
    trust = dict(unified_data_snapshot.get("trust") or {})
    overall_status = str(quality.get("overall_status") or "").upper()
    trust_score = _int_or_none(
        trust.get("overall_trust")
        if "overall_trust" in trust
        else business_metrics_snapshot.get("trust_score")
    )
    if overall_status == "HIGH" and (trust_score or 0) >= 85:
        return "GOOD"
    if overall_status == "LOW":
        return "WARNING"
    if overall_status:
        return "NORMAL"
    return "UNKNOWN"


def _costs_state(unified_data_snapshot, sku_registry_snapshot):
    costs = dict(unified_data_snapshot.get("costs") or {})
    registry_status = str(sku_registry_snapshot.get("registry_status") or "").upper()
    cost_status = str(costs.get("status") or "").upper()
    coverage = _float_or_none(
        costs.get("coverage_percent")
        if "coverage_percent" in costs
        else sku_registry_snapshot.get("coverage_percent")
    )
    if registry_status in ("PARTIAL", "MISSING", "UNAVAILABLE"):
        return "WARNING"
    if cost_status in ("DETAIL_REQUIRED", "UNAVAILABLE", "RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "API_ENDPOINT_ERROR", "ERROR", "UNKNOWN"):
        return "WARNING"
    if coverage is not None and coverage < 95.0:
        return "WARNING"
    if coverage is not None:
        return "GOOD"
    return "UNKNOWN"


def _cashflow_state(unified_data_snapshot):
    payments = dict(unified_data_snapshot.get("payments") or {})
    status = str(payments.get("status") or "").upper()
    if status in ("EXPECTED_TIMING_DIFFERENCE", "EXPECTED_NEXT_PERIOD"):
        return "NORMAL"
    if status == "NEEDS_REVIEW":
        return "WARNING"
    if status == "OK":
        return "GOOD"
    return "UNKNOWN"


def _find_cfo_summary(cfo_insights_snapshot):
    insights = list(cfo_insights_snapshot.get("insights") or [])
    if insights:
        first = dict(insights[0] or {})
        title = str(first.get("title") or "").strip()
        message = str(first.get("message") or "").strip()
        return f"{title}. {message}".strip(". ")
    actions = _text_list(cfo_insights_snapshot.get("actions"))
    if actions:
        return actions[0]
    return ""


def build_director_snapshot(
    period_snapshot=None,
    unified_data_snapshot=None,
    business_metrics_snapshot=None,
    financial_engine_snapshot=None,
    kpi_snapshot=None,
    cfo_insights_snapshot=None,
    decision_snapshot=None,
    advisor_v2_snapshot=None,
    sku_registry_snapshot=None,
):
    period_snapshot = dict(period_snapshot or {})
    unified_data_snapshot = dict(unified_data_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    kpi_snapshot = dict(kpi_snapshot or {})
    cfo_insights_snapshot = dict(cfo_insights_snapshot or {})
    decision_snapshot = dict(decision_snapshot or {})
    advisor_v2_snapshot = dict(advisor_v2_snapshot or {})
    sku_registry_snapshot = dict(sku_registry_snapshot or {})

    period = _period_payload(period_snapshot)
    financial_status = str(
        financial_engine_snapshot.get("status")
        or business_metrics_snapshot.get("official_status")
        or "UNAVAILABLE"
    )
    official_profit_available = bool(business_metrics_snapshot.get("official_available"))
    legacy_estimate_available = bool(
        business_metrics_snapshot.get("legacy_estimate_available")
        or financial_engine_snapshot.get("legacy_estimate_available")
    )
    legacy_gold_validation_status = str(financial_engine_snapshot.get("legacy_gold_validation_status") or "NOT_APPLICABLE")
    finance_blocked = _finance_blocked(financial_status, official_profit_available)
    kpi_summary = dict(kpi_snapshot.get("summary") or {})
    kpi_overall_status = str(kpi_summary.get("overall_status") or "UNKNOWN").upper()
    data_confidence = str(
        advisor_v2_snapshot.get("data_confidence")
        or decision_snapshot.get("data_confidence")
        or cfo_insights_snapshot.get("data_confidence")
        or kpi_snapshot.get("data_confidence")
        or "LOW"
    ).upper()
    if data_confidence not in DIRECTOR_ALLOWED_CONFIDENCE:
        data_confidence = "LOW"

    business_state = {
        "sales": _sales_state(unified_data_snapshot),
        "ads": _ads_state(unified_data_snapshot, business_metrics_snapshot),
        "finance": "BLOCKED" if finance_blocked else ("GOOD" if official_profit_available else "WARNING"),
        "data_quality": _data_quality_state(unified_data_snapshot, business_metrics_snapshot),
        "costs": _costs_state(unified_data_snapshot, sku_registry_snapshot),
        "cashflow": _cashflow_state(unified_data_snapshot),
    }

    main_risk = _item(
        "Финансовое закрытие периода пока не подтверждено",
        "Официальная финансовая картина временно недоступна, поэтому закрытие периода лучше не подтверждать раньше времени.",
        "HIGH",
        "BUSINESS_METRICS",
    )
    if not finance_blocked:
        kpi_warnings = [item for item in list(kpi_snapshot.get("kpis") or []) if str(item.get("status") or "").upper() == "WARNING"]
        if kpi_overall_status == "WARNING" and kpi_warnings:
            first_warning = dict(kpi_warnings[0] or {})
            main_risk = _item(
                first_warning.get("title") or "Есть зона внимания в KPI",
                first_warning.get("message") or "Один из ключевых KPI требует внимания.",
                first_warning.get("confidence") or data_confidence,
                "KPI",
            )
        elif str(kpi_overall_status or "") == "CRITICAL":
            main_risk = _item(
                "Есть критичный сигнал по KPI",
                "Часть ключевых показателей требует немедленного внимания.",
                "HIGH",
                "KPI",
            )

    advisor_main = dict(advisor_v2_snapshot.get("main_recommendation") or {})
    main_action = _item(
        "Дождаться восстановления Finance API и повторить финансовую проверку",
        "После восстановления официального финансового контура стоит повторно сверить закрытие периода.",
        "HIGH",
        "ADVISOR_V2",
    )
    if advisor_main:
        main_action = _item(
            _sanitize_text(advisor_main.get("title") or "Главное действие"),
            _sanitize_text(advisor_main.get("action") or advisor_main.get("message") or ""),
            advisor_main.get("confidence") or data_confidence,
            "ADVISOR_V2",
        )
    elif list(decision_snapshot.get("top_actions") or []):
        first_action = _sanitize_text(list(decision_snapshot.get("top_actions") or [])[0])
        main_action = _item("Главное действие на период", first_action, data_confidence, "DECISION")

    cfo_summary = _sanitize_text(_find_cfo_summary(cfo_insights_snapshot))
    advisor_summary = _sanitize_text((advisor_v2_snapshot.get("business_state") or {}).get("summary") or "")
    executive_parts = []
    if advisor_summary:
        executive_parts.append(advisor_summary)
    if cfo_summary:
        executive_parts.append(cfo_summary)
    if not executive_parts:
        executive_parts.append("Текущая сводка собрана из управленческих слоёв и требует обычной осторожности в интерпретации.")
    executive_summary = " ".join(_text_list(executive_parts))[:600]
    if legacy_estimate_available:
        executive_summary = _sanitize_text(
            f"{executive_summary} Legacy fallback mode active: finance available for reconciliation, but official new Finance API is not available."
        )[:600]
        if legacy_gold_validation_status == "MATCHED_LEGACY":
            executive_summary = _sanitize_text(
                f"{executive_summary} Legacy finance fallback совпал с майским эталоном, но новый Finance API всё ещё недоступен."
            )[:600]
        elif legacy_gold_validation_status == "NEEDS_REVIEW":
            executive_summary = _sanitize_text(
                f"{executive_summary} Legacy finance fallback требует проверки перед использованием."
            )[:600]

    today_focus = []
    for action in list(decision_snapshot.get("top_actions") or [])[:3]:
        today_focus.append(_sanitize_text(action))
    if not today_focus and advisor_main.get("action"):
        today_focus.append(_sanitize_text(advisor_main.get("action")))
    today_focus = _text_list(today_focus)[:3]

    what_not_to_do = _text_list(
        list(advisor_v2_snapshot.get("do_not_do") or []) +
        (["Не принимать решения по прибыльности отдельных SKU без полного покрытия себестоимости."] if business_state.get("costs") == "WARNING" else [])
    )[:4]

    next_checks = [
        "/finance api status",
        f"/financial engine {period.get('start_date')} {period.get('end_date')}",
        f"/advisor v2 {period.get('start_date')} {period.get('end_date')}",
    ]

    source_layers = ["UDL", "KPI Engine", "CFO Insights", "Decision Engine", "Advisor v2"]
    warnings = _text_list(list(advisor_v2_snapshot.get("warnings") or []) + list(decision_snapshot.get("warnings") or []))
    if legacy_estimate_available:
        warnings.append("legacy fallback mode")
    if legacy_gold_validation_status == "MATCHED_LEGACY":
        warnings.append("Legacy finance fallback совпал с майским эталоном, но новый Finance API всё ещё недоступен.")
    elif legacy_gold_validation_status == "NEEDS_REVIEW":
        warnings.append("Legacy finance fallback требует проверки перед использованием.")

    if finance_blocked:
        business_health = "WARNING"
    else:
        business_health = _summary_status_to_health(kpi_overall_status)
        if business_health == "UNKNOWN":
            business_health = "NORMAL"
    if str(kpi_overall_status or "") == "CRITICAL":
        business_health = "CRITICAL"

    if data_confidence == "LOW" and finance_blocked:
        status = "INSUFFICIENT_DATA"
    elif finance_blocked or business_health in ("WARNING", "CRITICAL"):
        status = "PARTIAL"
    else:
        status = "OK"

    return {
        "status": status,
        "period": period,
        "business_health": business_health,
        "data_confidence": data_confidence,
        "executive_summary": executive_summary,
        "main_risk": main_risk,
        "main_action": main_action,
        "business_state": business_state,
        "today_focus": today_focus,
        "what_not_to_do": what_not_to_do,
        "next_checks": next_checks,
        "source_layers": source_layers,
        "warnings": warnings,
    }


def _health_text(value):
    mapping = {
        "GOOD": "хорошее",
        "NORMAL": "нормальное",
        "WARNING": "с предупреждениями",
        "CRITICAL": "критичное",
        "UNKNOWN": "неопределённое",
    }
    return mapping.get(str(value or "").upper(), "неопределённое")


def _block_state_text(value):
    mapping = {
        "GOOD": "хорошо",
        "NORMAL": "нормально",
        "WARNING": "требует внимания",
        "BLOCKED": "временно заблокированы",
        "UNKNOWN": "неопределённо",
    }
    return mapping.get(str(value or "").upper(), "неопределённо")


def director_text(snapshot):
    snapshot = dict(snapshot or {})
    period = dict(snapshot.get("period") or {})
    business_state = dict(snapshot.get("business_state") or {})
    main_risk = dict(snapshot.get("main_risk") or {})
    main_action = dict(snapshot.get("main_action") or {})

    period_text = str(
        period.get("display_name")
        or (
            f'{period.get("start_date")}..{period.get("end_date")}'
            if period.get("start_date") and period.get("end_date")
            else "Unknown"
        )
    )

    lines = [
        "AI DIRECTOR",
        "",
        f"Период: {period_text}",
        "",
        "Состояние бизнеса:",
        f"Общий статус: {_health_text(snapshot.get('business_health'))}",
        f"Уверенность в данных: {_health_text(snapshot.get('data_confidence'))}",
        "",
        "Короткий вывод:",
        _sanitize_text(snapshot.get("executive_summary") or "-"),
        "",
        "Главный риск:",
        _sanitize_text(main_risk.get("title") or "-"),
        _sanitize_text(main_risk.get("message") or "-"),
        "",
        "Главное действие:",
        _sanitize_text(main_action.get("title") or "-"),
        _sanitize_text(main_action.get("message") or "-"),
        "",
        "Что сделать сегодня:",
    ]
    if "legacy fallback" in " ".join(str(item or "") for item in list(snapshot.get("warnings") or [])).lower():
        lines[12:12] = [
            "Legacy mode:",
            "Finance available: yes",
            "Official new finance: no",
            "Legacy estimate: yes",
            "",
        ]
    today_focus = list(snapshot.get("today_focus") or [])
    if today_focus:
        for idx, item in enumerate(today_focus, 1):
            lines.append(f"{idx}. {_sanitize_text(item)}")
    else:
        lines.append("1. Критичных действий на сегодня не выделено.")

    lines.extend(["", "Чего не делать:"])
    what_not_to_do = list(snapshot.get("what_not_to_do") or [])
    if what_not_to_do:
        for idx, item in enumerate(what_not_to_do, 1):
            lines.append(f"{idx}. {_sanitize_text(item)}")
    else:
        lines.append("1. Не принимать резких решений без дополнительной проверки деталей.")

    lines.extend(["", "Что проверить дальше:"])
    for idx, item in enumerate(list(snapshot.get("next_checks") or []), 1):
        lines.append(f"{idx}. {item}")

    lines.extend(["", "Куда перейти дальше:"])
    period_start = period.get("start_date")
    period_end = period.get("end_date")
    if str(business_state.get("finance") or "") in ("BLOCKED", "WARNING"):
        lines.append("1. /finance api status")
        lines.append(f"2. /financial engine {period_start} {period_end}")
        lines.append(f"3. /cfo insights {period_start} {period_end}")
    else:
        lines.append(f"1. /advisor v2 {period_start} {period_end}")
    lines.append(f"4. /kpi {period_start} {period_end}")
    lines.append(f"5. /decision {period_start} {period_end}")
    lines.append("6. /system audit")
    lines.append(f"7. /udl {period_start} {period_end}")

    lines.extend([
        "",
        "Состояние блоков:",
        f"Продажи: {_block_state_text(business_state.get('sales'))}",
        f"Реклама: {_block_state_text(business_state.get('ads'))}",
        f"Финансы: {_block_state_text(business_state.get('finance'))}",
        f"Данные: {_block_state_text(business_state.get('data_quality'))}",
        f"Себестоимость: {_block_state_text(business_state.get('costs'))}",
        f"Денежный поток: {_block_state_text(business_state.get('cashflow'))}",
        "",
        "Основание:",
    ])
    for item in list(snapshot.get("source_layers") or []):
        lines.append(f"- {item}")
    lines.extend([
        "",
        "Важно:",
        "AI Director не выполняет действий в кабинете WB. Это управленческая сводка.",
    ])
    return "\n".join(lines)
