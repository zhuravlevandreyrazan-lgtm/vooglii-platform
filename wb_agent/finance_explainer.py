"""Pure readonly finance explainability helpers."""

from wb_agent.formatting import money

__all__ = [
    "build_finance_explanation",
    "finance_explainability_lines",
]


def _component(name, label, amount, difference_abs, confidence, source, safe_to_use, already_inside_forpay, possible_overlap):
    amount = round(float(amount or 0), 2)
    share = round((amount / difference_abs * 100.0), 1) if difference_abs > 0.01 else 0.0
    return {
        "name": name,
        "label": label,
        "amount": amount,
        "share_of_difference": share,
        "confidence": confidence,
        "source": source,
        "safe_to_use": bool(safe_to_use),
        "already_inside_forPay": bool(already_inside_forpay),
        "possible_overlap": bool(possible_overlap),
    }


def build_finance_explanation(finance_health):
    finance_health = dict(finance_health or {})
    difference = round(float(finance_health.get("wb_difference_abs") or abs(float(finance_health.get("wb_difference") or 0))), 2)
    explained_total = round(float(finance_health.get("explained_total") or 0), 2)
    coverage = round((explained_total / difference * 100.0), 1) if difference > 0.01 else (100.0 if abs(explained_total) <= 0.01 else 0.0)
    reason = str(finance_health.get("finance_double_count_risk_reason") or finance_health.get("reconciliation_note") or "").strip()
    confirmed_overlap = bool(finance_health.get("finance_confirmed_double_count_risk"))
    possible_overlap = bool(finance_health.get("finance_possible_double_count_risk"))
    is_overexplained = bool(finance_health.get("is_overexplained"))

    if is_overexplained or coverage > 100.5:
        status = "OVEREXPLAINED"
    elif abs(coverage - 100.0) <= 0.5:
        status = "FULLY EXPLAINED"
    else:
        status = "UNEXPLAINED"

    if is_overexplained or confirmed_overlap:
        confidence = "LOW"
    elif possible_overlap:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    components = [
        _component("logistics", "Logistics", finance_health.get("logistics"), difference, "MEDIUM", "finance_raw_audit.delivery/logistics", False, True, False),
        _component("storage", "Storage", finance_health.get("storage"), difference, "MEDIUM", "finance_raw_audit.storage", False, True, False),
        _component("acquiring", "Acquiring", finance_health.get("acquiring"), difference, "LOW" if float(finance_health.get("acquiring") or 0) > 0.01 else "MEDIUM", "finance_raw_audit.acquiring_fee", False, True, True),
        _component("penalties", "Penalties", finance_health.get("penalties"), difference, "LOW" if float(finance_health.get("penalties") or 0) > 0.01 else "MEDIUM", "finance_raw_audit.penalty", False, True, True),
        _component("acceptance", "Acceptance", finance_health.get("acceptance"), difference, "LOW" if float(finance_health.get("acceptance") or 0) > 0.01 else "MEDIUM", "finance_raw_audit.acceptance/acceptance_fee", False, True, True),
        _component("deductions", "Deductions", finance_health.get("deductions"), difference, "LOW" if float(finance_health.get("deductions") or 0) > 0.01 else "MEDIUM", "finance_raw_audit.deduction", False, True, True),
        _component("other_deductions", "Other", finance_health.get("other_deductions"), difference, "LOW" if float(finance_health.get("other_deductions") or 0) > 0.01 else "MEDIUM", "finance_raw_audit.additional_payment + residual bridge bucket", False, True, True),
    ]
    components = [item for item in components if abs(float(item.get("amount") or 0)) > 0.01]

    if status == "OVEREXPLAINED":
        recommended_action = "Проверить строки Finance API, относящиеся к deductions и acquiring."
    elif status == "FULLY EXPLAINED":
        recommended_action = "Разница полностью объяснена."
    else:
        recommended_action = "Проверить необъяснённую часть difference и строки Finance API по периоду."

    if not reason:
        if status == "OVEREXPLAINED":
            reason = "Finance components overlap."
        elif status == "FULLY EXPLAINED":
            reason = "Difference is fully explained by visible WB-side components."
        else:
            reason = "Difference is not fully explained by visible WB-side components."

    return {
        "difference": difference,
        "explained_total": explained_total,
        "coverage_percent": coverage,
        "status": status,
        "confidence": confidence,
        "reason": reason,
        "recommended_action": recommended_action,
        "components": components,
        "unexplained_amount": round(max(0.0, difference - explained_total), 2),
        "overexplained_amount": round(max(0.0, explained_total - difference), 2),
    }


def finance_explainability_lines(snapshot):
    snapshot = dict(snapshot or {})
    components = list(snapshot.get("components") or [])
    lines = [
        "FINANCE EXPLAINABILITY",
        "",
        f'Difference: {money(snapshot.get("difference") or 0)}',
        "",
        "Explained:",
    ]
    if components:
        for item in components:
            lines.extend([
                f'• {item.get("label") or item.get("name") or "Component"}',
                f'{money(item.get("amount") or 0)}',
                f'{float(item.get("share_of_difference") or 0):.1f}%',
                "",
            ])
    else:
        lines.extend(["No visible WB-side components found.", ""])
    lines.extend([
        f'Coverage: {float(snapshot.get("coverage_percent") or 0):.1f}%',
        f'Status: {snapshot.get("status") or "UNKNOWN"}',
        f'Confidence: {snapshot.get("confidence") or "LOW"}',
        f'Reason: {snapshot.get("reason") or "-"}',
        f'Recommended action: {snapshot.get("recommended_action") or "-"}',
    ])
    return lines
