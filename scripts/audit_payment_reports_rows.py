from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
from vooglii_finance.customer_snapshot import build_customer_financial_snapshot
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot_dict


ROW_FIELDS = (
    "reason",
    "doc_type",
    "income_type",
    "revenue",
    "for_pay",
    "delivery",
    "storage",
    "deduction",
    "bank_payment",
)

MAPPING_ROWS = (
    ("reportId", "report_id", "-", "-", "-"),
    ("dateFrom", "date_from", "-", "-", "-"),
    ("dateTo", "date_to", "-", "-", "-"),
    ("reportType", "report_type", "-", "-", "-"),
    ("salesSum", "revenue", "wb_sale_amount", "wb_sale_amount / sales_revenue", "sales_revenue"),
    ("forPaySum", "for_pay", "wb_payout_amount", "wb_payout_amount / wb_payout", "wb_payout"),
    ("bankPaymentSum", "bank_payment", "wb_total_to_pay", "wb_total_to_pay", "wb_total_to_pay"),
    ("deliveryServiceSum", "delivery", "wb_logistics", "wb_logistics / logistics", "logistics"),
    ("paidStorageSum", "storage", "wb_storage", "wb_storage / storage", "storage"),
    ("deductionSum", "deduction", "wb_deductions", "wb_deductions", "wb_deductions"),
    ("penaltySum", "penalty", "-", "-", "-"),
    ("additionalPaymentSum", "additional_payment", "-", "-", "-"),
    ("docType", "doc_type", "audit only", "audit only", "audit only"),
    ("incomeType", "income_type", "audit only", "audit only", "audit only"),
    ("reason", "reason", "audit only", "audit only", "audit only"),
)


def _money(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def _print_section(title: str) -> None:
    print(title)
    print("-" * len(title))


def _telegram_surfaces(user_id: int, days) -> dict[str, dict]:
    pick = ("wb_sale_amount", "wb_payout_amount", "wb_total_to_pay", "wb_logistics", "wb_storage", "wb_deductions")
    return {
        "home": {key: telegram_bot._home_snapshot(user_id, days).get(key) for key in pick},
        "finance": {key: telegram_bot._finance_center_snapshot(user_id, days).get(key) for key in pick},
        "report": {key: telegram_bot._customer_report_snapshot(user_id, days).get(key) for key in pick},
    }


def _overlap_reference_rows(period_from: str, period_to: str) -> list[dict]:
    rows = []
    for row in telegram_bot._weekly_payout_reference_rows():
        period = str(row.get("period") or "")
        if ".." not in period:
            continue
        ref_start, ref_end = [part.strip() for part in period.split("..", 1)]
        if ref_start <= period_to and ref_end >= period_from:
            rows.append(dict(row))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit payment_reports_rows and its propagation to weekly/customer/telegram layers.")
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    period_from = date.fromisoformat(args.date_from)
    period_to = date.fromisoformat(args.date_to)
    days = (args.date_from, args.date_to)

    payment = telegram_bot._payment_reconciliation_snapshot(args.user_id, args.date_from, args.date_to)
    weekly = build_wb_weekly_snapshot_dict(args.user_id, period_from, period_to)
    customer = build_customer_financial_snapshot(args.user_id, period_from, period_to)
    telegram_surfaces = _telegram_surfaces(args.user_id, days)
    reference_rows = _overlap_reference_rows(args.date_from, args.date_to)

    _print_section("payment_reports_rows status")
    for key in (
        "payment_reports_source",
        "payment_reports_status",
        "payment_reports_message",
        "payment_reports_count",
        "payment_reports_total_revenue",
        "payment_reports_total_for_pay",
        "payment_reports_total_bank_payment",
        "payment_reports_total_delivery",
        "payment_reports_total_storage",
        "payment_reports_total_deduction",
    ):
        print(f"{key}: {payment.get(key)}")

    _print_section("weekly reference overlap")
    print(f"overlap_rows: {len(reference_rows)}")
    for index, row in enumerate(reference_rows, 1):
        print(
            f"{index}. report_id={row.get('report_id')} period={row.get('period')} "
            f"type={row.get('type')} payout={_money(row.get('payout'))}"
        )

    _print_section("payment_reports_rows")
    rows = list(payment.get("payment_reports_rows") or [])
    if not rows:
        print("No real WB API rows are present in payment_reports_rows.")
    for index, row in enumerate(rows, 1):
        print(f"row_{index}")
        print(f"report_id: {row.get('report_id') or '-'}")
        print(f"period_start: {row.get('period_start') or '-'}")
        print(f"period_end: {row.get('period_end') or '-'}")
        print(f"type: {row.get('type') or '-'}")
        for field_name in ROW_FIELDS:
            value = row.get(field_name)
            print(f"{field_name}: {_money(value) if field_name not in ('reason', 'doc_type', 'income_type') else (value or '-')}")
        print(f"raw_fields: {json.dumps(row.get('raw_fields') or [], ensure_ascii=False)}")
        print(f"raw_json: {row.get('raw_json') or '{}'}")
        print("")

    _print_section("mapping table")
    print("API field | payment_reports_rows column | wb_weekly_snapshot selected field | customer_snapshot | telegram")
    for api_field, payment_column, weekly_field, customer_field, telegram_field in MAPPING_ROWS:
        print(f"{api_field} | {payment_column} | {weekly_field} | {customer_field} | {telegram_field}")

    _print_section("wb_weekly_snapshot selected")
    for field_name in ("wb_sale_amount", "wb_payout_amount", "wb_total_to_pay", "wb_logistics", "wb_storage", "wb_deductions"):
        source = ((weekly.get("source_map") or {}).get(field_name) or {})
        print(
            f"{field_name}: value={_money(weekly.get(field_name))} "
            f"source={source.get('selected_source') or '-'} rows={source.get('rows') or 0}"
        )

    _print_section("customer_snapshot selected")
    for field_name in ("wb_sale_amount", "wb_payout_amount", "wb_total_to_pay", "wb_logistics", "wb_storage", "wb_deductions"):
        trace = ((customer.get("field_trace") or {}).get(field_name) or {})
        print(
            f"{field_name}: value={_money(customer.get(field_name))} "
            f"source={trace.get('selected_source') or '-'} table={trace.get('selected_table') or '-'}"
        )

    _print_section("telegram surfaces")
    for surface_name, values in telegram_surfaces.items():
        print(surface_name)
        for field_name in ("wb_sale_amount", "wb_payout_amount", "wb_total_to_pay", "wb_logistics", "wb_storage", "wb_deductions"):
            print(f"  {field_name}: {_money(values.get(field_name))}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
