"""Readonly regression test for the finance explainability engine."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wb_agent.finance_explainer import build_finance_explanation, finance_explainability_lines


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    snapshot = build_finance_explanation({
        "wb_difference": 88769.01,
        "wb_difference_abs": 88769.01,
        "explained_total": 110805.26,
        "logistics": 59833.62,
        "storage": 2686.16,
        "acquiring": 8712.48,
        "penalties": 10.00,
        "acceptance": 0.0,
        "deductions": 39563.00,
        "other_deductions": 0.0,
        "is_overexplained": True,
        "finance_confirmed_double_count_risk": True,
        "finance_possible_double_count_risk": True,
        "finance_double_count_risk_reason": "Finance components overlap.",
    })

    _assert(round(float(snapshot.get("coverage_percent") or 0), 1) == 124.8, "coverage_percent mismatch")
    _assert(str(snapshot.get("status") or "") == "OVEREXPLAINED", "status should be OVEREXPLAINED")
    _assert(str(snapshot.get("confidence") or "") == "LOW", "confidence should be LOW")
    _assert(round(float(snapshot.get("overexplained_amount") or 0), 2) == 22036.25, "overexplained amount mismatch")

    components = {item["name"]: item for item in (snapshot.get("components") or [])}
    _assert("logistics" in components, "logistics component missing")
    _assert("storage" in components, "storage component missing")
    _assert("acquiring" in components, "acquiring component missing")
    _assert("deductions" in components, "deductions component missing")
    _assert(round(float(components["logistics"]["share_of_difference"] or 0), 1) == 67.4, "logistics share mismatch")
    _assert(round(float(components["storage"]["share_of_difference"] or 0), 1) == 3.0, "storage share mismatch")
    _assert(round(float(components["acquiring"]["share_of_difference"] or 0), 1) == 9.8, "acquiring share mismatch")
    _assert(round(float(components["deductions"]["share_of_difference"] or 0), 1) == 44.6, "deductions share mismatch")
    _assert(bool(components["acquiring"]["possible_overlap"]) is True, "acquiring should be marked as possible overlap")
    _assert(bool(components["deductions"]["already_inside_forPay"]) is True, "deductions should be marked as already inside forPay")

    lines = finance_explainability_lines(snapshot)
    text = "\n".join(lines)
    for marker in ("FINANCE EXPLAINABILITY", "Difference:", "Coverage:", "Status: OVEREXPLAINED", "Confidence: LOW", "Recommended action:"):
        _assert(marker in text, f"missing marker {marker}")
    _assert("124.8%" in text, "coverage percent text missing")
    _assert("67.4%" in text, "logistics share text missing")

    print("FINANCE EXPLAINABILITY TEST OK")


if __name__ == "__main__":
    main()
