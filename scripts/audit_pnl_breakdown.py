from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_finance.customer_snapshot import build_customer_financial_snapshot_dict


def _money(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):,.2f}".replace(",", " ")


def _selected_source(snapshot, field_name: str) -> str:
    trace = dict((snapshot.get("field_trace") or {}).get(field_name) or {})
    return str(trace.get("selected_source") or "-")


def _is_closed(snapshot) -> bool:
    return str(snapshot.get("source_mode") or "") == "WB_NATIVE_CLOSED"


def _duplicate_checks(snapshot: dict) -> dict[str, bool]:
    expense_sources = {
        "advertising": _selected_source(snapshot, "advertising"),
        "logistics": _selected_source(snapshot, "wb_logistics"),
        "storage": _selected_source(snapshot, "wb_storage"),
        "acquiring": _selected_source(snapshot, "wb_acquiring"),
        "deductions": _selected_source(snapshot, "wb_deductions"),
        "other": _selected_source(snapshot, "other_expenses"),
        "penalties": _selected_source(snapshot, "penalties"),
    }
    closed = _is_closed(snapshot)
    payout_as_expense = any(source == "payment_reports.for_pay" for source in expense_sources.values())
    total_to_pay_as_expense = any(source == "payment_reports.bank_payment" for source in expense_sources.values())
    logistics_duplicate = closed and expense_sources["logistics"].startswith("finance_expense_events.")
    storage_duplicate = closed and expense_sources["storage"].startswith("finance_expense_events.")
    deductions_duplicate = closed and expense_sources["deductions"].startswith("finance_expense_events.")
    return {
        "payout_as_expense": payout_as_expense,
        "total_to_pay_as_expense": total_to_pay_as_expense,
        "logistics_duplicate": logistics_duplicate,
        "storage_duplicate": storage_duplicate,
        "deductions_duplicate": deductions_duplicate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    snapshot = dict(build_customer_financial_snapshot_dict(args.user_id, (args.date_from, args.date_to)))
    checks = _duplicate_checks(snapshot)

    print("P&L Breakdown")
    print()
    print(f"Revenue: {_money(snapshot.get('wb_sale_amount'))}")
    print(f"Cost: {_money(snapshot.get('cost_price'))}")
    print(f"Advertising: {_money(snapshot.get('advertising'))}")
    print(f"Logistics: {_money(snapshot.get('wb_logistics'))}")
    print(f"Storage: {_money(snapshot.get('wb_storage'))}")
    print(f"Acquiring: {_money(snapshot.get('wb_acquiring'))}")
    print(f"Deductions: {_money(snapshot.get('wb_deductions'))}")
    print(f"Other: {_money(snapshot.get('wb_other'))}")
    print(f"Penalties: {_money(snapshot.get('penalties'))}")
    print(f"Expenses total: {_money(snapshot.get('expenses_total'))}")
    print(f"Operational profit: {_money(snapshot.get('operational_profit'))}")
    print()
    print("Duplicate checks:")
    for name, failed in checks.items():
        print(f"- {name}: {'YES' if failed else 'NO'}")

    hard_failures = [name for name, failed in checks.items() if failed]
    if hard_failures:
        print()
        print("FAIL")
        print(", ".join(hard_failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
