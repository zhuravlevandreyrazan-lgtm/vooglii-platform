"""Readonly regression test for warning deduplication in profit audit output."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _count_occurrences(lines, needle):
    return sum(1 for line in lines if str(line).strip() == str(needle).strip())


def _extract_block(lines, start_marker, end_marker):
    collecting = False
    result = []
    for line in lines:
        text = str(line).strip()
        if not collecting and text == start_marker:
            collecting = True
            continue
        if collecting and text == end_marker:
            break
        if collecting:
            result.append(text)
    return result


def main():
    warning_overlap = "Finance components overlap detected. WB-side deduction bridge is informational only."
    warning_forpay = "Do not subtract WB-side components from forPay again."
    warning_official = "Official profit requires row-level compatible finance report."
    warning_base = "Current recommended profit base is operational payout model."

    deduped = telegram_bot.dedupe_warnings([
        "",
        warning_overlap,
        warning_forpay,
        warning_overlap,
        "   ",
        warning_official,
        warning_base,
        warning_forpay,
    ])
    _assert(
        deduped == [warning_overlap, warning_forpay, warning_official, warning_base],
        "dedupe_warnings should preserve first-seen order and remove blanks/duplicates",
    )

    original_profit_audit_snapshot = telegram_bot._profit_audit_snapshot
    try:
        telegram_bot._profit_audit_snapshot = lambda user, days: {
            "period_start": "2026-06-01",
            "period_end": "2026-06-28",
            "official_profit": 1.0,
            "management_profit": 2.0,
            "delta": 1.0,
            "overall_quality": "HIGH",
            "data_quality_score": 90.0,
            "advertising_health": {
                "status": "HIGH",
                "linkability_percent": 100.0,
                "duplicate_negative_spend": 0.0,
            },
            "trust_score": 35,
            "warnings": [
                warning_overlap,
                warning_overlap,
                warning_forpay,
                warning_forpay,
                warning_official,
                warning_base,
                warning_base,
            ],
            "verdict": "trust_low",
            "finance_health": {
                "coverage_percent": 100.0,
                "unexplained_total": 0.0,
                "reconciliation_status": "OVEREXPLAINED",
                "warnings": [
                    warning_overlap,
                    warning_overlap,
                    warning_forpay,
                    warning_official,
                    warning_base,
                    warning_base,
                ],
                "wb_difference": 1.0,
                "explained_total": 2.0,
                "finance_components_total": 2.0,
                "explained_vs_difference_delta": 1.0,
                "wb_difference_abs": 1.0,
                "is_overexplained": True,
                "overexplained_amount": 1.0,
                "finance_double_count_risk": True,
                "finance_double_count_risk_sources": ["deductions"],
                "finance_confirmed_double_count_risk": True,
                "finance_possible_double_count_risk": True,
                "finance_double_count_risk_reason": "raw overlapping components present in wb_difference",
                "finance_residual_debug": {},
            },
            "profit_reconciliation_debug": {
                "management_profit": 2.0,
                "official_profit": 1.0,
                "difference": 1.0,
                "components": {
                    "revenue": 10.0,
                    "wb_payout": 9.0,
                    "cost": 1.0,
                    "ads": 1.0,
                    "logistics": 1.0,
                    "storage": 1.0,
                    "penalties": 1.0,
                    "deductions": 1.0,
                    "taxes": None,
                    "other": 1.0,
                    "raw_other": 1.0,
                },
                "likely_reasons": ["reason"],
                "verdict": "difference needs manual review",
                "note": warning_overlap,
            },
            "profit_display_debug": {
                "revenue": 10.0,
                "payout": 9.0,
                "wb_deductions_already_in_payout": "yes",
                "cost_price": 1.0,
                "advertising": 1.0,
                "external_expenses": 0.0,
                "profit_before_tax_from_payout": 8.0,
                "tax_amount": None,
                "official_profit": 1.0,
                "double_subtraction_prevented": "yes",
                "note": "note",
            },
            "payout_verification_debug": {
                "payout_source_field": "field",
                "payout_is_after_wb_deductions": "yes",
                "official_profit_formula_detected": "formula",
                "double_subtraction_risk": "yes",
                "recommended_profit_base": "forPay - cost - advertising - external_expenses - tax",
                "reconciliation_status": "OVEREXPLAINED",
                "status": "DEGRADED",
                "model_status": "MATCHED",
                "ads_double_subtraction_status": "prevented",
                "warnings": [
                    warning_overlap,
                    warning_overlap,
                    warning_forpay,
                    warning_official,
                    warning_base,
                    warning_base,
                ],
            },
            "official_financial_profit": {"status": "UNAVAILABLE"},
            "financial_engine": {"status": "RATE_LIMIT", "source": "unavailable"},
            "official_profit_status": "UNRECONCILED",
            "management_profit_status": "OPERATIONAL",
            "reconciliation_status": "OVEREXPLAINED",
            "wb_payout_bridge": {
                "sales_revenue_total": 10.0,
                "sales_for_pay_total": 9.0,
                "wb_difference": 1.0,
                "finance_logistics": 1.0,
                "finance_storage": 1.0,
                "finance_acquiring": 1.0,
                "finance_penalties": 1.0,
                "finance_deductions": 1.0,
                "finance_other": 1.0,
                "finance_residual": 0.0,
                "explained_wb_deductions_total": 2.0,
                "bridge_delta": -1.0,
                "forPay_includes_wb_deductions": "yes",
                "double_subtraction_risk": "yes",
                "safe_profit_base": "forPay - cost - advertising - external_expenses - tax",
                "bridge_mode": "informational_only",
            },
            "profit_after_wb_costs": 8.0,
            "net_profit_after_tax": None,
        }

        text = telegram_bot._profit_audit_text("custom", ("2026-06-01", "2026-06-28"), 1)
        lines = [line.strip() for line in text.splitlines()]

        warnings_block = _extract_block(lines, "WARNINGS", "FINANCE DEBUG")
        finance_warnings_block = _extract_block(lines, "FINANCE WARNINGS", "TRUST SCORE")

        for warning in (warning_overlap, warning_forpay, warning_official, warning_base):
            _assert(
                _count_occurrences(warnings_block, f"* {warning}") == 1,
                f"warning should appear once in WARNINGS block: {warning}",
            )
            _assert(
                _count_occurrences(finance_warnings_block, warning) == 1,
                f"warning should appear once in FINANCE WARNINGS block: {warning}",
            )

        for index in range(len(lines) - 1):
            _assert(lines[index] != lines[index + 1], "profit audit text should not contain consecutive duplicate lines")

        print("PROFIT AUDIT WARNING DEDUP TEST OK")
    finally:
        telegram_bot._profit_audit_snapshot = original_profit_audit_snapshot


if __name__ == "__main__":
    main()
