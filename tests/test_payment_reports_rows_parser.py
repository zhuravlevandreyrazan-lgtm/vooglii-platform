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


def test_normalize_finance_report_row_accepts_real_alternative_revenue_field_names():
    row = {
        "reportId": "rep-2",
        "dateFrom": "2026-06-29",
        "dateTo": "2026-07-05",
        "createDate": "2026-07-06T10:00:00",
        "reportType": "main",
        "saleSum": 14046.08,
        "forPaySum": 15327.09,
        "bankPaymentSum": 9084.94,
        "deliveryServiceSum": 3463.06,
        "paidStorageSum": 631.09,
        "deductionSum": 2148.00,
        "currencyName": "RUB",
    }

    normalized = _normalize_finance_report_row(row)

    assert normalized["create_date"] == "2026-07-06T10:00:00"
    assert normalized["currency_name"] == "RUB"
    assert normalized["revenue"] == 14046.08


def test_normalize_finance_report_row_prioritizes_retail_amount_sum_after_sales_sum():
    row = {
        "reportId": "rep-3",
        "dateFrom": "2026-06-22",
        "dateTo": "2026-06-28",
        "createDate": "2026-06-29T10:00:00",
        "reportType": "1",
        "retailAmountSum": 7846.00,
        "forPaySum": 7000.00,
        "bankPaymentSum": 5000.00,
        "deliveryServiceSum": 1000.00,
        "paidStorageSum": 300.00,
        "deductionSum": 200.00,
    }

    normalized = _normalize_finance_report_row(row)

    assert normalized["revenue"] == 7846.00
