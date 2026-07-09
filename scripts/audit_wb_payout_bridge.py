from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot_dict


CLOSED_WEEKS = (
    ("2026-06-08", "2026-06-14"),
    ("2026-06-15", "2026-06-21"),
    ("2026-06-22", "2026-06-28"),
    ("2026-06-29", "2026-07-05"),
)


def _money(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def _pick(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            return round(float(value), 2)
        except Exception:
            continue
    return None


def _sum_known(*values: Any) -> float | None:
    known: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            known.append(float(value))
        except Exception:
            continue
    if not known:
        return None
    return round(sum(known), 2)


def _trace_source(snapshot: dict[str, Any], field_name: str) -> str:
    source_map = dict(snapshot.get("source_map") or {})
    field = dict(source_map.get(field_name) or {})
    return str(field.get("selected_source") or "-")


def _print_field(label: str, value: Any, source: str | None = None) -> None:
    suffix = f" | source: {source}" if source else ""
    print(f"{label}: {_money(value)}{suffix}")


def _collect_week(user_id: int, week_start: str, week_end: str) -> dict[str, Any]:
    days = (week_start, week_end)
    payment = telegram_bot._payment_reconciliation_snapshot(user_id, week_start, week_end)
    weekly = build_wb_weekly_snapshot_dict(user_id, date.fromisoformat(week_start), date.fromisoformat(week_end))
    mgmt = telegram_bot._report_mgmt_snapshot(user_id, days)
    finance = telegram_bot.get_finance_difference_snapshot(user_id, week_start, week_end)

    revenue = _pick(payment.get("payment_reports_total_revenue"), weekly.get("wb_sale_amount"), mgmt.get("revenue"))
    for_pay = _pick(payment.get("payment_reports_total_for_pay"), weekly.get("wb_payout_amount"), payment.get("sales_for_pay_total"))
    bank_payment = _pick(payment.get("payment_reports_total_bank_payment"), weekly.get("wb_total_to_pay"))
    delivery = _pick(payment.get("payment_reports_total_delivery"), weekly.get("wb_logistics"))
    storage = _pick(payment.get("payment_reports_total_storage"), weekly.get("wb_storage"))
    deduction = _pick(payment.get("payment_reports_total_deduction"), weekly.get("wb_deductions"))
    penalty = _pick(payment.get("payment_reports_total_penalty"), weekly.get("penalties"))
    additional_payment = _pick(payment.get("payment_reports_total_additional_payment"))
    acquiring = _pick(weekly.get("wb_acquiring"), finance.get("acquiring"))
    advertising = _pick(weekly.get("advertising"), mgmt.get("advertising"))
    cost_price = _pick(mgmt.get("cost_price"))
    other = _pick(weekly.get("wb_other"), finance.get("explicit_other_deductions"), mgmt.get("other"))

    calculated_bank_payment = None
    bank_payment_residual = None
    if None not in (for_pay, delivery, storage, deduction, penalty, additional_payment):
        calculated_bank_payment = round(
            float(for_pay)
            - float(delivery)
            - float(storage)
            - float(deduction)
            - float(penalty)
            + float(additional_payment),
            2,
        )
        if bank_payment is not None:
            bank_payment_residual = round(calculated_bank_payment - float(bank_payment), 2)

    revenue_to_forpay_delta = None
    wb_side_known_total = None
    revenue_to_forpay_residual = None
    if revenue is not None and for_pay is not None:
        revenue_to_forpay_delta = round(float(revenue) - float(for_pay), 2)
        wb_side_known_total = _sum_known(delivery, storage, acquiring, deduction, penalty, other)
        if wb_side_known_total is not None:
            revenue_to_forpay_residual = round(float(revenue_to_forpay_delta) - float(wb_side_known_total), 2)

    operational_profit = None
    if None not in (revenue, cost_price, advertising, delivery, storage, acquiring, deduction, penalty):
        operational_profit = round(
            float(revenue)
            - float(cost_price)
            - float(advertising)
            - float(delivery)
            - float(storage)
            - float(acquiring)
            - float(deduction)
            - float(penalty)
            - float(other or 0.0),
            2,
        )

    return {
        "week": f"{week_start}..{week_end}",
        "payment": payment,
        "weekly": weekly,
        "mgmt": mgmt,
        "finance": finance,
        "revenue": revenue,
        "for_pay": for_pay,
        "bank_payment": bank_payment,
        "delivery": delivery,
        "storage": storage,
        "deduction": deduction,
        "penalty": penalty,
        "additional_payment": additional_payment,
        "acquiring": acquiring,
        "advertising": advertising,
        "cost_price": cost_price,
        "other": other,
        "calculated_bank_payment": calculated_bank_payment,
        "bank_payment_residual": bank_payment_residual,
        "revenue_to_forpay_delta": revenue_to_forpay_delta,
        "wb_side_known_total": wb_side_known_total,
        "revenue_to_forpay_residual": revenue_to_forpay_residual,
        "operational_profit": operational_profit,
    }


def _print_week(snapshot: dict[str, Any]) -> None:
    week = snapshot["week"]
    payment = dict(snapshot["payment"] or {})
    weekly = dict(snapshot["weekly"] or {})

    print()
    print(f"WEEK {week}")
    print("=" * (5 + len(week)))
    _print_field("revenue", snapshot["revenue"], _trace_source(weekly, "wb_sale_amount"))
    _print_field("for_pay", snapshot["for_pay"], _trace_source(weekly, "wb_payout_amount"))
    _print_field("bank_payment", snapshot["bank_payment"], _trace_source(weekly, "wb_total_to_pay"))
    _print_field("delivery", snapshot["delivery"], _trace_source(weekly, "wb_logistics"))
    _print_field("storage", snapshot["storage"], _trace_source(weekly, "wb_storage"))
    _print_field("deduction", snapshot["deduction"], _trace_source(weekly, "wb_deductions"))
    _print_field("penalty", snapshot["penalty"], _trace_source(weekly, "penalties"))
    _print_field("additional_payment", snapshot["additional_payment"], "payment_reports.total_additional_payment")
    _print_field("acquiring", snapshot["acquiring"], _trace_source(weekly, "wb_acquiring"))
    _print_field("advertising", snapshot["advertising"], _trace_source(weekly, "advertising"))
    _print_field("cost_price", snapshot["cost_price"], "report_mgmt.cost_price")
    _print_field("other", snapshot["other"], _trace_source(weekly, "wb_other"))

    print()
    print("Bridge 1")
    print("--------")
    print("for_pay - delivery - storage - deduction - penalty + additional_payment = calculated_bank_payment")
    _print_field("calculated_bank_payment", snapshot["calculated_bank_payment"])
    _print_field("reported_bank_payment", snapshot["bank_payment"])
    _print_field("residual", snapshot["bank_payment_residual"])

    print()
    print("Bridge 2")
    print("--------")
    print("revenue - for_pay = revenue_to_forpay_delta")
    _print_field("revenue_to_forpay_delta", snapshot["revenue_to_forpay_delta"])
    _print_field("known_wb_side_total", snapshot["wb_side_known_total"])
    _print_field("residual", snapshot["revenue_to_forpay_residual"])

    print()
    print("P&L")
    print("---")
    print("revenue - cost_price - advertising - delivery - storage - acquiring - deduction - penalty - other = operational_profit")
    _print_field("operational_profit", snapshot["operational_profit"])

    print()
    print("Diagnostics")
    print("-----------")
    print(f"payment_reports_source: {payment.get('payment_reports_source') or '-'}")
    print(f"payment_reports_status: {payment.get('payment_reports_status') or '-'}")
    print(f"payment_reports_count: {int(payment.get('payment_reports_count') or 0)}")
    print(f"weekly_warning_count: {len(list(weekly.get('warnings') or []))}")
    for item in list(weekly.get("warnings") or []):
        print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit WB payout bridge for the four June/July 2026 closed weeks.")
    parser.add_argument("--user-id", required=True, type=int)
    args = parser.parse_args()

    for week_start, week_end in CLOSED_WEEKS:
        _print_week(_collect_week(args.user_id, week_start, week_end))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
