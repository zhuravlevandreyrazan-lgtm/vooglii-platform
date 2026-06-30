"""Pure readonly helpers for the Financial Engine module.

This module contains only deterministic normalization and formatting helpers.
It does not perform API calls, DB writes, cache mutations, or Telegram I/O.
"""

from wb_agent.formatting import money

FINANCIAL_ENGINE_AVAILABLE_STATUSES = ("MATCHED", "PARTIAL")
FINANCIAL_ENGINE_RUNTIME_UNAVAILABLE_STATUSES = (
    "LEGACY_FALLBACK",
    "RATE_LIMIT",
    "FORBIDDEN",
    "UNAUTHORIZED",
    "UNAVAILABLE",
    "DETAIL_REQUIRED",
    "API_ENDPOINT_ERROR",
    "ERROR",
    "PARTIAL_COST_MISSING",
)

__all__ = [
    "FINANCIAL_ENGINE_AVAILABLE_STATUSES",
    "FINANCIAL_ENGINE_RUNTIME_UNAVAILABLE_STATUSES",
    "normalize_financial_engine_report",
    "finance_detail_extract_rows",
    "financial_detail_number",
    "financial_detail_text",
    "financial_detail_int",
    "normalize_financial_detail_row",
    "financial_engine_runtime_unavailable",
    "financial_engine_may_regression_lines",
    "render_financial_engine_text",
]


def normalize_financial_engine_report(row):
    row = dict(row or {})
    return {
        "report_id": str(row.get("report_id") or row.get("reportId") or "").strip() or None,
        "report_type": str(row.get("type") or row.get("report_type") or "").strip() or None,
        "period_start": str(row.get("period_start") or row.get("date_from") or row.get("dateFrom") or "").strip()[:10] or None,
        "period_end": str(row.get("period_end") or row.get("date_to") or row.get("dateTo") or "").strip()[:10] or None,
        "sales_total": row.get("sales_total"),
        "for_pay_total": round(float(row.get("for_pay") or row.get("forPaySum") or 0), 2),
        "payment_total": round(float(row.get("bank_payment") or row.get("bankPaymentSum") or 0), 2),
        "bank_payment_sum": round(float(row.get("bank_payment") or row.get("bankPaymentSum") or 0), 2),
        "delivery_service_sum": round(float(row.get("delivery") or row.get("deliveryServiceSum") or 0), 2),
        "storage_sum": round(float(row.get("storage") or row.get("paidStorageSum") or 0), 2),
        "deduction_sum": round(float(row.get("deduction") or row.get("deductionSum") or 0), 2),
        "penalty_sum": round(float(row.get("penalty") or row.get("penaltySum") or 0), 2),
        "additional_payment_sum": round(float(row.get("additional_payment") or row.get("additionalPaymentSum") or 0), 2),
        "commission_total": row.get("commission_total"),
        "payment_schedule": str(row.get("payment_schedule") or row.get("paymentSchedule") or "").strip() or None,
    }


def finance_detail_extract_rows(payload):
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []

    direct_lists = [
        payload.get("data"),
        payload.get("details"),
        payload.get("rows"),
        payload.get("items"),
        payload.get("result"),
        payload.get("reportRows"),
        payload.get("report_rows"),
    ]
    for candidate in direct_lists:
        if isinstance(candidate, list):
            return [row for row in candidate if isinstance(row, dict)]
        if isinstance(candidate, dict):
            nested = finance_detail_extract_rows(candidate)
            if nested:
                return nested

    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            nested = finance_detail_extract_rows(value)
            if nested:
                return nested
    return []


def financial_detail_number(row, *keys):
    row = dict(row or {})
    for key in keys:
        value = row.get(key)
        if value in (None, "", "-"):
            continue
        try:
            return round(float(value), 2)
        except Exception:
            continue
    return 0.0


def financial_detail_text(row, *keys):
    row = dict(row or {})
    for key in keys:
        value = row.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return ""


def financial_detail_int(row, *keys):
    value = financial_detail_number(row, *keys)
    try:
        return int(round(value))
    except Exception:
        return 0


def normalize_financial_detail_row(row, report_row=None):
    row = dict(row or {})
    report_row = dict(report_row or {})
    sales_total = financial_detail_number(
        row,
        "saleSum", "sale_sum", "retailAmount", "retail_amount", "retailPrice",
        "retail_price", "totalPrice", "total_price", "priceWithDisc",
        "price_with_disc", "finishedPrice", "finished_price", "income",
    )
    for_pay_total = financial_detail_number(
        row,
        "forPay", "for_pay", "forPaySum", "for_pay_sum", "ppvzForPay",
        "ppvz_for_pay", "toTransfer", "to_transfer",
    )
    wb_commission_total = financial_detail_number(
        row,
        "commission", "commissionSum", "commission_sum", "retailCommission",
        "retail_commission", "ppvzVw", "ppvz_vw", "supplierReward",
        "supplier_reward", "vwCommission", "vw_commission",
    )
    payment_services_commission_total = financial_detail_number(
        row,
        "acquiringFee", "acquiring_fee", "acquiring", "paymentProcessingFee",
        "payment_processing_fee", "bankCommission", "bank_commission",
    )
    logistics_total = financial_detail_number(
        row,
        "deliveryRub", "delivery_rub", "deliveryAmount", "delivery_amount",
        "deliveryServiceSum", "delivery_service_sum", "logistics",
        "logisticsSum", "logistics_sum",
    )
    storage_total = financial_detail_number(
        row,
        "storageFee", "storage_fee", "paidStorage", "paid_storage",
        "paidStorageSum", "paid_storage_sum", "storage", "storageSum",
        "storage_sum",
    )
    acceptance_total = financial_detail_number(
        row,
        "acceptance", "acceptanceSum", "acceptance_sum",
    )
    deduction_base = financial_detail_number(
        row,
        "deduction", "deductionSum", "deduction_sum", "deductions",
        "deductionsSum", "deductions_sum", "otherDeduction", "other_deduction",
    )
    penalty_total = financial_detail_number(
        row,
        "penalty", "penaltySum", "penalty_sum",
    )
    additional_payment_total = financial_detail_number(
        row,
        "additionalPayment", "additional_payment", "additionalPaymentSum",
        "additional_payment_sum",
    )
    deductions_total = round(
        deduction_base + acceptance_total + penalty_total + additional_payment_total + payment_services_commission_total,
        2,
    )
    quantity = financial_detail_int(
        row,
        "quantity", "qty", "saleQty", "sale_qty", "saQuantity",
        "sa_quantity", "realizationreport_id_quantity", "amount",
    )
    if quantity == 0:
        quantity = max(
            0,
            financial_detail_int(row, "saleQty", "sale_qty", "quantitySold")
            - financial_detail_int(row, "returnQty", "return_qty"),
        )
    if quantity == 0 and sales_total > 0 and for_pay_total < 0:
        quantity = -1

    resolved_report_id = str(
        report_row.get("report_id")
        or row.get("reportId")
        or row.get("reportID")
        or row.get("realizationreport_id")
        or ""
    ).strip() or None
    article = financial_detail_text(
        row,
        "supplierArticle", "supplier_article", "saName", "sa_name",
        "vendorCode", "vendor_code", "barcodeArticle", "barcode_article",
    )
    nm_id = financial_detail_text(
        row,
        "nmId", "nmID", "nmid", "nm_id", "nm",
    )
    return {
        "report_id": resolved_report_id,
        "period_start": report_row.get("period_start"),
        "period_end": report_row.get("period_end"),
        "sku": article or None,
        "nm_id": nm_id or None,
        "quantity": int(quantity or 0),
        "sales_total": round(sales_total, 2),
        "for_pay_total": round(for_pay_total, 2),
        "wb_commission_total": round(wb_commission_total, 2),
        "payment_services_commission_total": round(payment_services_commission_total, 2),
        "logistics_total": round(logistics_total, 2),
        "storage_total": round(storage_total, 2),
        "acceptance_total": round(acceptance_total, 2),
        "deductions_total": round(deductions_total, 2),
        "deduction_base_total": round(deduction_base, 2),
        "penalty_total": round(penalty_total, 2),
        "additional_payment_total": round(additional_payment_total, 2),
        "subject": financial_detail_text(row, "subjectName", "subject_name", "subject") or None,
        "brand": financial_detail_text(row, "brandName", "brand_name", "brand") or None,
        "raw_row": row,
    }


def financial_engine_runtime_unavailable(status):
    return str(status or "").strip().upper() in FINANCIAL_ENGINE_RUNTIME_UNAVAILABLE_STATUSES


def financial_engine_may_regression_lines(start_date, end_date, is_gold_standard_may_period, gold_standard_may_expected_fixture):
    if not is_gold_standard_may_period(start_date, end_date):
        return []
    expected = gold_standard_may_expected_fixture()
    return [
        "Эталон мая подтверждён:",
        f'официальная чистая прибыль по Gold Standard = {money(expected.get("official_net_profit") or 0)}',
        "Это regression reference, не runtime API source.",
    ]


def render_financial_engine_text(snapshot, start_date, end_date):
    snapshot = dict(snapshot or {})
    legacy_mode = str(snapshot.get("status") or "").upper() == "LEGACY_FALLBACK"
    lines = [
        "FINANCIAL ENGINE",
        "",
        f'Source: {snapshot.get("source") or "unavailable"}',
        f'Status: {snapshot.get("status") or "UNAVAILABLE"}',
        f'Cooldown active: {"yes" if snapshot.get("cooldown_active") else "no"}',
        f'Cooldown until: {snapshot.get("cooldown_until") or "-"}',
        f'Cooldown source: {snapshot.get("cooldown_source") or "manual"}',
        f'Period: {snapshot.get("period") or f"{start_date}..{end_date}"}',
        f'Validation: {snapshot.get("validation_status") or "NOT_VALIDATED"}',
        f'Reports: {int(snapshot.get("reports_count") or 0)}',
        f'Detail rows: {int(snapshot.get("detail_rows_count") or 0)}',
        "",
        "WB financial totals:",
        f'Продажи WB: {money(snapshot.get("wb_sales_total") or 0)}' if snapshot.get("wb_sales_total") is not None else "Продажи WB: not available on list-level snapshot",
        f'Итого к оплате WB: {money(snapshot.get("wb_payment_total") or 0)}' if snapshot.get("wb_payment_total") is not None else "Итого к оплате WB: not available",
        f'Комиссия WB: {money(snapshot.get("wb_commission_total") or 0)}' if snapshot.get("wb_commission_total") is not None else "Комиссия WB: DETAIL_REQUIRED",
        f'Эквайринг / платёжные сервисы: {money(snapshot.get("payment_services_commission_total") or 0)}' if snapshot.get("payment_services_commission_total") is not None else "Эквайринг / платёжные сервисы: DETAIL_REQUIRED",
        f'Логистика: {money(snapshot.get("logistics_total") or 0)}' if snapshot.get("logistics_total") is not None else "Логистика: not available",
        f'Хранение: {money(snapshot.get("storage_total") or 0)}' if snapshot.get("storage_total") is not None else "Хранение: not available",
        f'Удержания: {money(snapshot.get("deductions_total") or 0)}' if snapshot.get("deductions_total") is not None else "Удержания: not available",
        f'Реклама: {"включена в удержания WB" if str(snapshot.get("ads_handling") or "") == "INCLUDED_IN_WB_DEDUCTIONS" else str(snapshot.get("ads_handling") or "unknown")}',
        "",
        "Profit:",
        f'Итого к оплате WB: {money(snapshot.get("wb_payment_total") or 0)}' if snapshot.get("wb_payment_total") is not None else "Итого к оплате WB: not available",
        f'Себестоимость: {money(snapshot.get("cost_total") or 0)}' if snapshot.get("cost_total") is not None else f'Себестоимость: {snapshot.get("cost_status") or "unknown"}',
        f'Cost coverage: {float(snapshot.get("cost_coverage_percent") or 0):.1f}%',
        f'Налог: {money(snapshot.get("tax_amount") or 0)}' if snapshot.get("tax_amount") is not None else "Налог: not available",
        f'Официальная чистая прибыль: {money(snapshot.get("official_net_profit") or 0)}' if snapshot.get("official_net_profit") is not None else "Официальная чистая прибыль: DETAIL_REQUIRED",
        "",
        "Warnings:",
    ]
    if legacy_mode:
        lines.extend([
            "",
            "SOURCE MODE",
            "Источник: legacy finance API",
            "Это временный fallback, потому что новый Finance API не принимает текущий токен.",
            "Расчёт можно использовать для сверки, но для final official mode нужен новый Finance API.",
        ])
        if snapshot.get("legacy_financial_profit_estimate") is not None:
            lines.append(f'Legacy financial profit estimate: {money(snapshot.get("legacy_financial_profit_estimate") or 0)}')
    if legacy_mode and str(snapshot.get("period_start") or "") == "2026-05-01" and str(snapshot.get("period_end") or "") == "2026-05-31":
        legacy_delta = dict(snapshot.get("legacy_gold_delta") or {})
        lines.extend([
            "",
            "LEGACY GOLD STANDARD CHECK",
            f'status: {snapshot.get("legacy_gold_validation_status") or "NOT_APPLICABLE"}',
            f'payment delta: {money(legacy_delta.get("payment_delta") or 0)}' if legacy_delta.get("payment_delta") is not None else "payment delta: -",
            f'cost delta: {money(legacy_delta.get("cost_delta") or 0)}' if legacy_delta.get("cost_delta") is not None else "cost delta: -",
            f'tax delta: {money(legacy_delta.get("tax_delta") or 0)}' if legacy_delta.get("tax_delta") is not None else "tax delta: -",
            f'net profit delta: {money(legacy_delta.get("net_profit_delta") or 0)}' if legacy_delta.get("net_profit_delta") is not None else "net profit delta: -",
        ])
        validation_status = str(snapshot.get("legacy_gold_validation_status") or "")
        if validation_status == "MATCHED_LEGACY":
            lines.append("Legacy fallback совпал с майским эталоном в пределах допуска.")
        elif validation_status == "NEEDS_REVIEW":
            lines.append("Legacy fallback не совпал с майским эталоном. Нужна проверка нормализации rows.")
    warnings = list(snapshot.get("warnings") or [])
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")
    missing_cost_skus = list(snapshot.get("missing_cost_skus") or [])
    if missing_cost_skus:
        lines.extend([
            "",
            "Missing cost SKU:",
            ", ".join(missing_cost_skus[:20]),
        ])
    return "\n".join(lines)
