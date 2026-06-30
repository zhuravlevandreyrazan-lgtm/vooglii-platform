"""Pure readonly Unified Data Layer helpers.

This module aggregates existing snapshot dicts into one normalized read-only
structure. It does not call APIs, SQL, cache, or Telegram.
"""

from wb_agent.formatting import money

UDL_ALLOWED_SOURCE_STATUSES = (
    "OK",
    "AVAILABLE",
    "PARTIAL",
    "MATCHED",
    "LEGACY_FALLBACK",
    "DETAIL_REQUIRED",
    "PARTIAL_COST_MISSING",
    "FORBIDDEN",
    "UNAUTHORIZED",
    "UNAVAILABLE",
    "RATE_LIMIT",
    "API_ENDPOINT_ERROR",
    "ERROR",
    "UNKNOWN",
    "EXPECTED_NEXT_PERIOD",
    "NEEDS_REVIEW",
)

__all__ = [
    "UDL_ALLOWED_SOURCE_STATUSES",
    "build_unified_data_snapshot",
    "build_unified_data_light_snapshot",
    "unified_data_text",
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


def _list_text(value):
    result = []
    for item in list(value or []):
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _dedup_text_list(items):
    result = []
    seen = set()
    for item in _list_text(items):
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _finance_cost_unavailable_reason(finance_status):
    finance_status = str(finance_status or "UNKNOWN")
    if finance_status == "LEGACY_FALLBACK":
        return None
    if finance_status == "DETAIL_REQUIRED":
        return "DETAIL_REQUIRED"
    if finance_status in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "API_ENDPOINT_ERROR", "ERROR"):
        return "unavailable"
    return None


def _build_source_info(name, *, status, available, source, last_updated=None, rows=None, coverage=None, warnings=None):
    normalized_status = str(status or "UNKNOWN")
    if normalized_status in ("HIGH", "MEDIUM"):
        normalized_status = "AVAILABLE"
    elif normalized_status == "LOW":
        normalized_status = "PARTIAL" if available else "UNAVAILABLE"
    elif normalized_status == "EXPECTED_TIMING_DIFFERENCE":
        normalized_status = "EXPECTED_NEXT_PERIOD"
    return {
        "name": str(name),
        "status": normalized_status,
        "available": bool(available),
        "source": str(source or "unknown"),
        "last_updated": last_updated,
        "rows": _int_or_none(rows),
        "coverage": _float_or_none(coverage),
        "warnings": _list_text(warnings),
    }


def build_unified_data_snapshot(
    period,
    sales_snapshot=None,
    advertising_snapshot=None,
    financial_engine_snapshot=None,
    payment_snapshot=None,
    business_metrics_snapshot=None,
    data_quality_snapshot=None,
    trust_snapshot=None,
):
    sales_snapshot = dict(sales_snapshot or {})
    advertising_snapshot = dict(advertising_snapshot or {})
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    payment_snapshot = dict(payment_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    data_quality_snapshot = dict(data_quality_snapshot or {})
    trust_snapshot = dict(trust_snapshot or {})

    if isinstance(period, (tuple, list)) and len(period) == 2:
        period_start, period_end = str(period[0]), str(period[1])
    else:
        period_start = str((business_metrics_snapshot.get("period_start") or financial_engine_snapshot.get("period_start") or payment_snapshot.get("period_start") or ""))
        period_end = str((business_metrics_snapshot.get("period_end") or financial_engine_snapshot.get("period_end") or payment_snapshot.get("period_end") or ""))

    sales_rows = (
        sales_snapshot.get("sales_rows_count")
        if "sales_rows_count" in sales_snapshot
        else sales_snapshot.get("rows")
    )
    ads_rows = advertising_snapshot.get("supplier_article_rows")
    finance_rows = financial_engine_snapshot.get("detail_rows_count") or financial_engine_snapshot.get("reports_count")
    payment_rows = payment_snapshot.get("payment_reports_count")

    overall_warnings = []
    for bucket in (
        sales_snapshot.get("warnings"),
        advertising_snapshot.get("warnings"),
        financial_engine_snapshot.get("warnings"),
        payment_snapshot.get("warnings"),
        business_metrics_snapshot.get("official_warnings"),
        business_metrics_snapshot.get("operational_warnings"),
    ):
        overall_warnings.extend(_list_text(bucket))
    overall_warnings = _dedup_text_list(overall_warnings)

    finance_status = str(financial_engine_snapshot.get("status") or "UNKNOWN")
    cost_unavailable_reason = _finance_cost_unavailable_reason(finance_status)
    cost_total = _float_or_none(business_metrics_snapshot.get("official_cost_total"))
    cost_coverage_percent = _float_or_none(business_metrics_snapshot.get("cost_coverage_percent") or financial_engine_snapshot.get("cost_coverage_percent"))
    cost_trust = _int_or_none(trust_snapshot.get("cost_trust") if "cost_trust" in trust_snapshot else financial_engine_snapshot.get("cost_coverage_percent"))
    trust_notes = []
    if cost_unavailable_reason is not None:
        cost_total = None
        cost_coverage_percent = None
        cost_trust = None
        trust_notes.append("cost trust unavailable until finance detail rows are available")

    sources = {
        "sales": _build_source_info(
            "sales",
            status=(data_quality_snapshot.get("sales") or {}).get("status") or "UNKNOWN",
            available=(sales_snapshot.get("sales_revenue_total") is not None) or (sales_snapshot.get("revenue") is not None),
            source="local_db_snapshot",
            last_updated=(data_quality_snapshot.get("sales") or {}).get("last_success"),
            rows=sales_rows,
            coverage=None,
            warnings=(sales_snapshot.get("warnings") or []),
        ),
        "ads": _build_source_info(
            "ads",
            status=advertising_snapshot.get("status") or (data_quality_snapshot.get("advertising") or {}).get("status") or "UNKNOWN",
            available=advertising_snapshot.get("total_spend") is not None,
            source="local_db_snapshot",
            last_updated=advertising_snapshot.get("last_success") or (data_quality_snapshot.get("advertising") or {}).get("last_success"),
            rows=ads_rows,
            coverage=advertising_snapshot.get("linkability_percent"),
            warnings=advertising_snapshot.get("warnings"),
        ),
        "finance": _build_source_info(
            "finance",
            status=financial_engine_snapshot.get("status") or "UNKNOWN",
            available=financial_engine_snapshot.get("source") not in (None, "", "unavailable"),
            source=financial_engine_snapshot.get("source") or "unavailable",
            last_updated=None,
            rows=finance_rows,
            coverage=financial_engine_snapshot.get("cost_coverage_percent"),
            warnings=financial_engine_snapshot.get("warnings"),
        ),
        "payments": _build_source_info(
            "payments",
            status=payment_snapshot.get("status") or payment_snapshot.get("payment_reconciliation_status") or "UNKNOWN",
            available=payment_snapshot.get("sales_for_pay_total") is not None,
            source=payment_snapshot.get("payment_reports_source") or "unknown",
            last_updated=None,
            rows=payment_rows,
            coverage=None,
            warnings=payment_snapshot.get("warnings"),
        ),
    }

    snapshot = {
        "period": {
            "start": period_start,
            "end": period_end,
        },
        "sources": sources,
        "sales": {
            "revenue": _float_or_none(sales_snapshot.get("sales_revenue_total") if "sales_revenue_total" in sales_snapshot else sales_snapshot.get("revenue")),
            "for_pay": _float_or_none(sales_snapshot.get("sales_for_pay_total") if "sales_for_pay_total" in sales_snapshot else sales_snapshot.get("payout")),
            "rows": _int_or_none(sales_rows),
        },
        "advertising": {
            "total_spend": _float_or_none(advertising_snapshot.get("total_spend")),
            "linked_spend": _float_or_none(advertising_snapshot.get("linked_spend")),
            "unlinked_spend": _float_or_none(advertising_snapshot.get("unlinked_spend")),
            "linkability_percent": _float_or_none(advertising_snapshot.get("linkability_percent")),
            "status": str(advertising_snapshot.get("status") or "UNKNOWN"),
        },
        "finance": {
            "status": str(financial_engine_snapshot.get("status") or "UNKNOWN"),
            "source": str(financial_engine_snapshot.get("source") or "unavailable"),
            "wb_payment_total": _float_or_none(financial_engine_snapshot.get("wb_payment_total")),
            "official_net_profit": _float_or_none(financial_engine_snapshot.get("official_net_profit")),
            "legacy_financial_profit_estimate": _float_or_none(financial_engine_snapshot.get("legacy_financial_profit_estimate")),
            "official_new_finance_available": bool(financial_engine_snapshot.get("official_new_finance_available")),
            "legacy_estimate_available": bool(financial_engine_snapshot.get("legacy_estimate_available")),
            "cost_coverage_percent": _float_or_none(financial_engine_snapshot.get("cost_coverage_percent")),
            "missing_cost_skus": _list_text(financial_engine_snapshot.get("missing_cost_skus")),
        },
        "payments": {
            "status": str(payment_snapshot.get("status") or "UNKNOWN"),
            "sales_for_pay_total": _float_or_none(payment_snapshot.get("sales_for_pay_total")),
            "received_total": _float_or_none(payment_snapshot.get("received_total") or payment_snapshot.get("weekly_payout_total_all")),
            "expected_next_payout": _float_or_none(payment_snapshot.get("expected_next_payout") or payment_snapshot.get("estimated_pending_payout")),
            "source": str(payment_snapshot.get("payment_reports_source") or "unknown"),
        },
        "costs": {
            "cost_total": cost_total,
            "coverage_percent": cost_coverage_percent,
            "status": cost_unavailable_reason or "AVAILABLE",
            "missing_cost_skus": _list_text(business_metrics_snapshot.get("missing_cost_skus") or financial_engine_snapshot.get("missing_cost_skus")),
        },
        "business_metrics": dict(business_metrics_snapshot),
        "quality": {
            "overall_score": _float_or_none(data_quality_snapshot.get("overall_score")),
            "overall_status": str(data_quality_snapshot.get("overall_status") or "UNKNOWN"),
            "sales_status": str((data_quality_snapshot.get("sales") or {}).get("status") or "UNKNOWN"),
            "advertising_status": str((data_quality_snapshot.get("advertising") or {}).get("status") or "UNKNOWN"),
            "finance_status": str((data_quality_snapshot.get("finance") or {}).get("status") or "UNKNOWN"),
            "notes": trust_notes,
        },
        "trust": {
            "overall_trust": _int_or_none(trust_snapshot.get("overall_trust") if "overall_trust" in trust_snapshot else business_metrics_snapshot.get("trust_score")),
            "finance_trust": _int_or_none(trust_snapshot.get("finance_trust") if "finance_trust" in trust_snapshot else business_metrics_snapshot.get("trust_score")),
            "ads_trust": _int_or_none(trust_snapshot.get("ads_trust") if "ads_trust" in trust_snapshot else advertising_snapshot.get("linkability_percent")),
            "sales_trust": _int_or_none(trust_snapshot.get("sales_trust") if "sales_trust" in trust_snapshot else data_quality_snapshot.get("overall_score")),
            "cost_trust": cost_trust,
        },
        "warnings": overall_warnings,
    }
    return snapshot


def build_unified_data_light_snapshot(
    period,
    sales_snapshot=None,
    advertising_snapshot=None,
    financial_engine_snapshot=None,
    payment_snapshot=None,
    business_metrics_snapshot=None,
    data_quality_snapshot=None,
    trust_snapshot=None,
):
    sales_snapshot = dict(sales_snapshot or {})
    advertising_snapshot = dict(advertising_snapshot or {})
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    payment_snapshot = dict(payment_snapshot or {})
    business_metrics_snapshot = dict(business_metrics_snapshot or {})
    data_quality_snapshot = dict(data_quality_snapshot or {})
    trust_snapshot = dict(trust_snapshot or {})

    if isinstance(period, (tuple, list)) and len(period) == 2:
        period_start, period_end = str(period[0]), str(period[1])
    else:
        period_start = str(business_metrics_snapshot.get("period_start") or "")
        period_end = str(business_metrics_snapshot.get("period_end") or "")

    finance_status = str(financial_engine_snapshot.get("status") or "UNKNOWN")
    cost_unavailable_reason = _finance_cost_unavailable_reason(finance_status)
    cost_coverage_percent = _float_or_none(
        business_metrics_snapshot.get("cost_coverage_percent")
        or financial_engine_snapshot.get("cost_coverage_percent")
    )
    overall_trust = _int_or_none(
        trust_snapshot.get("overall_trust")
        if "overall_trust" in trust_snapshot
        else business_metrics_snapshot.get("trust_score")
    )
    revenue = _float_or_none(
        sales_snapshot.get("sales_revenue_total")
        if "sales_revenue_total" in sales_snapshot
        else sales_snapshot.get("revenue")
    )
    ads_total_spend = _float_or_none(advertising_snapshot.get("total_spend"))
    ads_share = None
    if ads_total_spend not in (None, 0) and revenue not in (None, 0):
        ads_share = round((ads_total_spend / revenue) * 100.0, 1)

    overall_warnings = []
    for bucket in (
        financial_engine_snapshot.get("warnings"),
        business_metrics_snapshot.get("official_warnings"),
        business_metrics_snapshot.get("operational_warnings"),
    ):
        overall_warnings.extend(_list_text(bucket))
    overall_warnings = _dedup_text_list(overall_warnings)

    snapshot = {
        "period": {
            "start": period_start,
            "end": period_end,
        },
        "sources": {
            "sales": _build_source_info(
                "sales",
                status=(data_quality_snapshot.get("sales") or {}).get("status") or "UNKNOWN",
                available=revenue is not None,
                source="local_db_snapshot",
                last_updated=(data_quality_snapshot.get("sales") or {}).get("last_success"),
                rows=sales_snapshot.get("sales_rows_count") if "sales_rows_count" in sales_snapshot else sales_snapshot.get("rows"),
                warnings=sales_snapshot.get("warnings"),
            ),
            "ads": _build_source_info(
                "ads",
                status=advertising_snapshot.get("status") or (data_quality_snapshot.get("advertising") or {}).get("status") or "UNKNOWN",
                available=ads_total_spend is not None,
                source="local_db_snapshot",
                last_updated=advertising_snapshot.get("last_success") or (data_quality_snapshot.get("advertising") or {}).get("last_success"),
                rows=advertising_snapshot.get("supplier_article_rows"),
                coverage=advertising_snapshot.get("linkability_percent"),
                warnings=advertising_snapshot.get("warnings"),
            ),
            "finance": _build_source_info(
                "finance",
                status=finance_status,
                available=financial_engine_snapshot.get("source") not in (None, "", "unavailable"),
                source=financial_engine_snapshot.get("source") or "unavailable",
                rows=financial_engine_snapshot.get("detail_rows_count") or financial_engine_snapshot.get("reports_count"),
                coverage=financial_engine_snapshot.get("cost_coverage_percent"),
                warnings=financial_engine_snapshot.get("warnings"),
            ),
            "payments": _build_source_info(
                "payments",
                status=payment_snapshot.get("status") or "UNKNOWN",
                available=payment_snapshot.get("sales_for_pay_total") is not None,
                source=payment_snapshot.get("payment_reports_source") or "unknown",
                rows=payment_snapshot.get("payment_reports_count"),
                warnings=payment_snapshot.get("warnings"),
            ),
        },
        "sales": {
            "revenue": revenue,
            "for_pay": _float_or_none(
                sales_snapshot.get("sales_for_pay_total")
                if "sales_for_pay_total" in sales_snapshot
                else sales_snapshot.get("payout")
            ),
            "rows": _int_or_none(
                sales_snapshot.get("sales_rows_count")
                if "sales_rows_count" in sales_snapshot
                else sales_snapshot.get("rows")
            ),
        },
        "advertising": {
            "total_spend": ads_total_spend,
            "linked_spend": _float_or_none(advertising_snapshot.get("linked_spend")),
            "unlinked_spend": _float_or_none(advertising_snapshot.get("unlinked_spend")),
            "linkability_percent": _float_or_none(advertising_snapshot.get("linkability_percent")),
            "share_of_revenue_percent": ads_share,
            "status": str(advertising_snapshot.get("status") or "UNKNOWN"),
        },
        "finance": {
            "status": finance_status,
            "source": str(financial_engine_snapshot.get("source") or "unavailable"),
            "wb_payment_total": _float_or_none(financial_engine_snapshot.get("wb_payment_total")),
            "official_net_profit": _float_or_none(financial_engine_snapshot.get("official_net_profit")),
            "legacy_financial_profit_estimate": _float_or_none(financial_engine_snapshot.get("legacy_financial_profit_estimate")),
            "official_new_finance_available": bool(financial_engine_snapshot.get("official_new_finance_available")),
            "legacy_estimate_available": bool(financial_engine_snapshot.get("legacy_estimate_available")),
            "cost_coverage_percent": _float_or_none(financial_engine_snapshot.get("cost_coverage_percent")),
            "missing_cost_skus": _list_text(financial_engine_snapshot.get("missing_cost_skus")),
        },
        "payments": {
            "status": str(payment_snapshot.get("status") or "UNKNOWN"),
            "sales_for_pay_total": _float_or_none(payment_snapshot.get("sales_for_pay_total")),
            "received_total": _float_or_none(payment_snapshot.get("weekly_payout_total_all")),
            "expected_next_payout": _float_or_none(payment_snapshot.get("expected_next_payout")),
            "source": str(payment_snapshot.get("payment_reports_source") or "unknown"),
        },
        "costs": {
            "cost_total": None if cost_unavailable_reason is not None else _float_or_none(business_metrics_snapshot.get("official_cost_total")),
            "coverage_percent": None if cost_unavailable_reason is not None else cost_coverage_percent,
            "status": cost_unavailable_reason or "AVAILABLE",
            "missing_cost_skus": _list_text(business_metrics_snapshot.get("missing_cost_skus") or financial_engine_snapshot.get("missing_cost_skus")),
        },
        "quality": {
            "overall_score": _float_or_none(data_quality_snapshot.get("overall_score")),
            "overall_status": str(data_quality_snapshot.get("overall_status") or "UNKNOWN"),
            "sales_status": str((data_quality_snapshot.get("sales") or {}).get("status") or "UNKNOWN"),
            "advertising_status": str((data_quality_snapshot.get("advertising") or {}).get("status") or "UNKNOWN"),
            "finance_status": str((data_quality_snapshot.get("finance") or {}).get("status") or "UNKNOWN"),
            "notes": ["cost trust unavailable until finance detail rows are available"] if cost_unavailable_reason is not None else [],
        },
        "trust": {
            "overall_trust": overall_trust,
            "finance_trust": _int_or_none(trust_snapshot.get("finance_trust") if "finance_trust" in trust_snapshot else overall_trust),
            "ads_trust": _int_or_none(trust_snapshot.get("ads_trust") if "ads_trust" in trust_snapshot else advertising_snapshot.get("linkability_percent")),
            "sales_trust": _int_or_none(trust_snapshot.get("sales_trust") if "sales_trust" in trust_snapshot else data_quality_snapshot.get("overall_score")),
            "cost_trust": None if cost_unavailable_reason is not None else _int_or_none(trust_snapshot.get("cost_trust") if "cost_trust" in trust_snapshot else cost_coverage_percent),
        },
        "warnings": overall_warnings,
    }
    return snapshot


def unified_data_text(snapshot):
    snapshot = dict(snapshot or {})
    period = dict(snapshot.get("period") or {})
    sources = dict(snapshot.get("sources") or {})
    sales = dict(snapshot.get("sales") or {})
    advertising = dict(snapshot.get("advertising") or {})
    finance = dict(snapshot.get("finance") or {})
    payments = dict(snapshot.get("payments") or {})
    business_metrics = dict(snapshot.get("business_metrics") or {})
    quality = dict(snapshot.get("quality") or {})
    trust = dict(snapshot.get("trust") or {})
    warnings = _list_text(snapshot.get("warnings"))
    costs = dict(snapshot.get("costs") or {})

    def _source_line(name):
        item = dict(sources.get(name) or {})
        return f'{name}: {item.get("status") or "UNKNOWN"} | available: {"yes" if item.get("available") else "no"} | source: {item.get("source") or "unknown"}'

    lines = [
        "UNIFIED DATA LAYER",
        "",
        f'Period: {period.get("start") or "-"}..{period.get("end") or "-"}',
        "",
        "Sources",
        _source_line("sales"),
        _source_line("ads"),
        _source_line("finance"),
        _source_line("payments"),
        "",
        "Sales",
        f'revenue: {money(sales.get("revenue") or 0)}' if sales.get("revenue") is not None else "revenue: unavailable",
        f'for pay: {money(sales.get("for_pay") or 0)}' if sales.get("for_pay") is not None else "for pay: unavailable",
        "",
        "Ads",
        f'total spend: {money(advertising.get("total_spend") or 0)}' if advertising.get("total_spend") is not None else "total spend: unavailable",
        f'linkability: {float(advertising.get("linkability_percent") or 0):.1f}%',
        "",
        "Finance",
        f'status: {finance.get("status") or "UNKNOWN"}',
        f'official net profit: {money(finance.get("official_net_profit") or 0)}' if finance.get("official_net_profit") is not None else "official net profit: unavailable",
        f'official new finance: {"yes" if finance.get("official_new_finance_available") else "no"}',
        f'legacy estimate: {money(finance.get("legacy_financial_profit_estimate") or 0)}' if finance.get("legacy_estimate_available") and finance.get("legacy_financial_profit_estimate") is not None else f'legacy estimate: {"yes" if finance.get("legacy_estimate_available") else "no"}',
        "",
        "Payments",
        f'status: {payments.get("status") or "UNKNOWN"}',
        f'received: {money(payments.get("received_total") or 0)}' if payments.get("received_total") is not None else "received: unavailable",
        "",
        "Business Metrics",
        f'official status: {business_metrics.get("official_status") or "UNKNOWN"}',
        f'operational available: {"yes" if business_metrics.get("operational_available") else "no"}',
        "",
        "Quality",
        f'overall score: {float(quality.get("overall_score") or 0):.1f}',
        f'overall status: {quality.get("overall_status") or "UNKNOWN"}',
        "",
        "Overall Trust",
        f'overall: {trust.get("overall_trust") if trust.get("overall_trust") is not None else "-"}',
        f'finance: {trust.get("finance_trust") if trust.get("finance_trust") is not None else "-"}',
        f'ads: {trust.get("ads_trust") if trust.get("ads_trust") is not None else "-"}',
        f'sales: {trust.get("sales_trust") if trust.get("sales_trust") is not None else "-"}',
        f'cost: {trust.get("cost_trust") if trust.get("cost_trust") is not None else (costs.get("status") or "unavailable")}',
        "",
        "Warnings",
    ]
    quality_notes = _list_text(quality.get("notes"))
    if quality_notes:
        lines.extend(["", "Quality Notes:"])
        lines.extend([f"- {item}" for item in quality_notes])
    if warnings:
        lines.extend([f"- {item}" for item in warnings[:20]])
    else:
        lines.append("- none")
    return "\n".join(lines)
