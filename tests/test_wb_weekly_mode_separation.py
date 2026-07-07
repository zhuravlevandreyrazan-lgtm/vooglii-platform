from __future__ import annotations

from datetime import date

from vooglii_validation.models import FinancialMode, ValidationMetricResult, ValidationResult
from vooglii_validation.report_builder import build_validation_report_text


def test_weekly_mode_report_marks_management_context_as_non_parity():
    result = ValidationResult(
        user_id=42,
        period_from=date(2026, 6, 29),
        period_to=date(2026, 7, 5),
        reference_hash="hash-3",
        parity_score=100.0,
        metrics=[
            ValidationMetricResult(
                metric="revenue",
                wb_value=1500.0,
                vooglii_value=1500.0,
                delta=0.0,
                tolerance=1.0,
                status="PASS",
                source="wb_sale_amount",
                root_cause=None,
            )
        ],
        failed_metrics=[],
        warnings=["Weekly parity compares the WB weekly reference against WB-aligned source layers, not management P&L."],
        status="PASS",
        mode=FinancialMode.WB_WEEKLY_PARITY,
        snapshot_summary={"wb_sale_amount": 1500.0},
        management_context={"sales_revenue": 9000.0, "wb_payout": 5000.0, "net_profit": 3000.0, "finance_confidence": "LOW"},
    )

    text = build_validation_report_text(result)

    assert "WB Parity" in text
    assert "Management Context" in text
    assert "не влияет на parity score" in text
    assert "Management revenue: 9 000.00 ₽" in text
