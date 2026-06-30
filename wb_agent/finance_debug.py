"""Read-only finance debug text helpers.

This module contains only pure formatting helpers that accept prepared
snapshots and return text lines. No SQL, API, or business calculations.
"""

from wb_agent.formatting import money

__all__ = [
    "finance_verdict_lines",
    "finance_bucket_debug_lines",
    "finance_raw_article_detail_lines",
    "finance_debug_lines",
]


def _dedupe_warning_lines(warnings):
    unique_items = []
    seen = set()
    for item in list(warnings or []):
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique_items.append(text)
    return unique_items


def finance_verdict_lines(snapshot):
    snapshot = snapshot or {}
    confirmed_risk = bool(snapshot.get("finance_confirmed_double_count_risk"))
    possible_risk = bool(snapshot.get("finance_possible_double_count_risk"))
    overexplained = bool(snapshot.get("is_overexplained"))
    confirmed_sources = snapshot.get("finance_confirmed_double_count_risk_sources") or []
    residual_debug = snapshot.get("finance_residual_debug") or {}
    if overexplained:
        finance_status = "HIGH RISK"
    elif confirmed_risk:
        finance_status = "NEEDS REVIEW"
    elif possible_risk:
        finance_status = "WATCH"
    else:
        finance_status = "OK"
    if "deductions" in confirmed_sources:
        main_risk = "deductions overlap with WB promotion / advertising"
    elif "acquiring" in confirmed_sources:
        main_risk = "acquiring may already be included in payout-side WB difference"
    elif confirmed_sources:
        main_risk = f'{confirmed_sources[0]} may overlap with wb_difference'
    elif possible_risk:
        main_risk = snapshot.get("finance_double_count_risk_reason") or "possible overlap needs checking"
    else:
        main_risk = "no confirmed double count signal"
    residual_line = "balancing item, not raw duplicate"
    if str(residual_debug.get("residual_is_balancing_item") or "no") != "yes":
        residual_line = snapshot.get("finance_double_count_risk_reason") or "residual needs manual review"
    return [
        "FINANCE VERDICT",
        f'coverage: {float(snapshot.get("coverage_with_residual_percent") or 0):.1f}% with residual / {float(snapshot.get("real_coverage_percent") or 0):.1f}% real',
        f'overexplained: {"yes" if overexplained else "no"}',
        f'confirmed risk: {"yes" if confirmed_risk else "no"}',
        f'main risk: {main_risk}',
        f'residual: {residual_line}',
        f'status: {finance_status}',
    ]


def finance_bucket_debug_lines(snapshot):
    snapshot = snapshot or {}
    finance_bucket_debug = snapshot.get("finance_bucket_debug") or {}
    lines = ["FINANCE BUCKET DEBUG", ""]
    for bucket_name in ("acquiring", "deductions", "other_deductions"):
        bucket = finance_bucket_debug.get(bucket_name) or {}
        lines.append(bucket_name.upper())
        lines.append(f'total: {money(bucket.get("total_amount") or 0)}')
        lines.append(f'share of wb difference: {float(bucket.get("share_of_wb_difference_percent") or 0):.1f}%')
        lines.append(f'articles: {int(bucket.get("articles_count") or 0)}')
        lines.append("top:")
        top_articles = bucket.get("top_articles") or []
        if top_articles:
            for idx, row in enumerate(top_articles, 1):
                lines.append(
                    f'{idx}. {row["article_name"]} — {money(row["amount"])} ({float(row.get("share") or 0):.1f}%)'
                )
        else:
            lines.append("no raw articles found")
        lines.append(f'possible_overlap: {"yes" if bucket.get("possible_overlap") else "no"}')
        lines.append(f'classification: {bucket.get("bucket_classification") or "empty"}')
        lines.append(f'risk level: {bucket.get("bucket_risk_level") or "LOW"}')
        lines.append(f'explanation: {bucket.get("bucket_explanation") or "-"}')
        lines.append(f'risk: {bucket.get("risk_comment") or "-"}')
        lines.append("")
    warnings = _dedupe_warning_lines(snapshot.get("warnings") or [])
    if warnings:
        lines.extend(["", "FINANCE WARNINGS"])
        for item in warnings:
            lines.append(str(item))
    return lines


def finance_raw_article_detail_lines(snapshot):
    snapshot = snapshot or {}
    raw_article_debug = snapshot.get("finance_raw_article_debug") or {}
    raw_article_rows = raw_article_debug.get("rows") or []
    lines = ["RAW FINANCE ARTICLE DETAIL", "article_name | amount | target_bucket | possible_overlap"]
    if raw_article_rows:
        for row in raw_article_rows:
            lines.append(
                f'{row["article_name"]} | {money(row["amount"])} | {row["target_bucket"]} | {row["possible_overlap"]}'
            )
    else:
        lines.append("Нет raw finance article rows для acquiring / deductions / other_deductions за период.")
    lines.extend([
        "",
        f'acquiring_raw_articles_total: {money((raw_article_debug.get("bucket_totals") or {}).get("acquiring") or 0)}',
        f'deductions_raw_articles_total: {money((raw_article_debug.get("bucket_totals") or {}).get("deductions") or 0)}',
        f'other_deductions_raw_articles_total: {money((raw_article_debug.get("bucket_totals") or {}).get("other_deductions") or 0)}',
        "Примечание: article_name агрегируется как operation_type -> doc_type_name -> payment_type -> bonus_type_name -> subject_name -> brand_name.",
    ])
    return lines


def finance_debug_lines(snapshot, include_header=True):
    snapshot = snapshot or {}
    risk_sources = snapshot.get("finance_double_count_risk_sources") or []
    residual_debug = snapshot.get("finance_residual_debug") or {}
    lines = []
    if include_header:
        lines.extend(["FINANCE DEBUG", ""])
    lines.extend([
        f'wb_difference: {money(snapshot.get("wb_difference") or 0)}',
        f'explained_total: {money(snapshot.get("explained_total") or 0)}',
        f'finance_components_total: {money(snapshot.get("finance_components_total") or 0)}',
        f'delta: {money(snapshot.get("explained_vs_difference_delta") or 0)}',
        f'reconciliation_status: {snapshot.get("reconciliation_status") or "unknown"}',
        f'wb_difference_abs: {money(snapshot.get("wb_difference_abs") or 0)}',
        f'overexplained: {"yes" if snapshot.get("is_overexplained") else "no"}',
        f'overexplained_amount: {money(snapshot.get("overexplained_amount") or 0)}',
        f'double_count_risk: {"yes" if snapshot.get("finance_double_count_risk") else "no"}',
        f'risk_source: {", ".join(risk_sources) if risk_sources else "-"}',
        f'finance_confirmed_double_count_risk: {"yes" if snapshot.get("finance_confirmed_double_count_risk") else "no"}',
        f'finance_possible_double_count_risk: {"yes" if snapshot.get("finance_possible_double_count_risk") else "no"}',
        f'finance_double_count_risk_reason: {snapshot.get("finance_double_count_risk_reason") or "-"}',
        "",
        "FINANCE RESIDUAL DEBUG",
        f'residual_other_deductions: {money(residual_debug.get("residual_other_deductions") or snapshot.get("residual_other_deductions") or 0)}',
        f'residual_source_type: {residual_debug.get("residual_source_type") or "unknown"}',
        f'residual_formula: {residual_debug.get("residual_formula") or "-"}',
        f'residual_abs: {money(residual_debug.get("residual_abs") or 0)}',
        f'residual_share_of_difference: {float(residual_debug.get("residual_share_of_wb_difference_percent") or 0):.1f}%',
        f'residual_share_of_unexplained_percent: {float(residual_debug.get("residual_share_of_unexplained_percent") or 0):.1f}%',
        f'residual_is_balancing_item: {residual_debug.get("residual_is_balancing_item") or "no"}',
        f'residual_can_double_count: {residual_debug.get("residual_can_double_count") or "no"}',
        f'residual_confidence: {residual_debug.get("residual_confidence") or "LOW"}',
        f'confirmed_double_count_risk: {"yes" if snapshot.get("finance_confirmed_double_count_risk") else "no"}',
        f'possible_double_count_risk: {"yes" if snapshot.get("finance_possible_double_count_risk") else "no"}',
        f'risk_reason: {snapshot.get("finance_double_count_risk_reason") or "-"}',
    ])
    if snapshot.get("is_overexplained"):
        lines.extend([
            "",
            "FINANCE OVEREXPLAINED RISK",
            "explained_total превышает абсолютный wb_difference; проверьте residual bucket и WB-компоненты на повторный учёт.",
        ])
    warnings = _dedupe_warning_lines(snapshot.get("warnings") or [])
    if warnings:
        lines.extend(["", "FINANCE WARNINGS"])
        for item in warnings:
            lines.append(str(item))
    return lines
