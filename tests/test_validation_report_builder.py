from __future__ import annotations

from datetime import date

from vooglii_validation.models import FinancialMode, ValidationMetricResult, ValidationResult
from vooglii_validation.report_builder import build_validation_report_text


def test_validation_report_builder_outputs_delta_and_root_cause():
    result = ValidationResult(
        user_id=42,
        period_from=date(2026, 6, 29),
        period_to=date(2026, 7, 5),
        reference_hash="hash-1",
        parity_score=99.6,
        metrics=[
            ValidationMetricResult(
                metric="advertising",
                wb_value=2171.61,
                vooglii_value=2171.62,
                delta=0.01,
                tolerance=1.0,
                status="PASS",
                source="advertising",
                root_cause="rounding_difference",
            )
        ],
        failed_metrics=[],
        warnings=[],
        status="PASS",
        mode=FinancialMode.WB_WEEKLY_PARITY,
        management_context={"sales_revenue": 23000.0, "wb_payout": 18000.0, "net_profit": 5000.0, "finance_confidence": "HIGH"},
    )

    text = build_validation_report_text(result)

    assert "Финансовая сертификация WB" in text
    assert "Режим: Сверка с официальным отчётом WB" in text
    assert "Parity Score:" in text
    assert "advertising:" in text
    assert "Δ: 0.01 ₽" in text
    assert "Причина: Небольшая разница округления." in text
    assert "Management Context" in text
