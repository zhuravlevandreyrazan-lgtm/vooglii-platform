from __future__ import annotations

import json

from vooglii_telegram.legacy_bot import _normalize_finance_report_row


def test_normalize_finance_report_row_uses_real_wb_api_fields_only():
    row = {
        "reportId": "rep-1",
        "dateFrom": "2026-06-29",
        "dateTo": "2026-07-05",
        "createDate": "2026-07-06T10:00:00",
        "reportType": "main",
        "salesSum": 14046.08,
        "forPaySum": 15327.09,
        "bankPaymentSum": 9084.94,
        "deliveryServiceSum": 3463.06,
        "paidStorageSum": 631.09,
        "deductionSum": 2148.00,
        "penaltySum": 10.0,
        "additionalPaymentSum": 5.0,
        "paymentSchedule": "weekly",
        "currencyName": "RUB",
        "payment_total": 999999.0,
        "delivery": 999999.0,
        "storage": 999999.0,
        "deductions": 999999.0,
    }

    normalized = _normalize_finance_report_row(row)

    assert normalized["report_id"] == "rep-1"
    assert normalized["period_start"] == "2026-06-29"
    assert normalized["period_end"] == "2026-07-05"
    assert normalized["type"] == "main"
    assert normalized["revenue"] == 14046.08
    assert normalized["for_pay"] == 15327.09
    assert normalized["bank_payment"] == 9084.94
    assert normalized["delivery"] == 3463.06
    assert normalized["storage"] == 631.09
    assert normalized["deduction"] == 2148.00
    assert "payment_total" in normalized["raw_fields"]
    assert json.loads(normalized["raw_json"])["payment_total"] == 999999.0
