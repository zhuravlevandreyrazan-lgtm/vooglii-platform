from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
from vooglii_finance.bridges import build_finance_source_integrity_report, get_finance_expense_event_trace
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def _print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _table_stats(cur: sqlite3.Cursor, table: str, user_column: str, date_column: str, amount_expr: str, user_id: int, start_date: str, end_date: str) -> dict[str, object]:
    row = cur.execute(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            MIN(substr({date_column},1,10)) AS min_date,
            MAX(substr({date_column},1,10)) AS max_date,
            ROUND(COALESCE(SUM({amount_expr}),0),2) AS total_amount
        FROM {table}
        WHERE {user_column}=? AND substr({date_column},1,10) BETWEEN ? AND ?
        """,
        (int(user_id), str(start_date), str(end_date)),
    ).fetchone()
    return dict(row or {})


def _print_layer(title: str, payload: dict[str, object]) -> None:
    _print_section(title)
    print(f"Rows: {int(payload.get('rows_count') or 0)}")
    print(f"Amount: {_money(payload.get('total_amount'))}")
    print(f"Min Date: {payload.get('min_date') or '-'}")
    print(f"Max Date: {payload.get('max_date') or '-'}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--trace-category", dest="trace_category")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        sales = _table_stats(cur, "sales", "telegram_id", "sale_date", "price_with_disc", args.user_id, args.date_from, args.date_to)
        orders = _table_stats(cur, "orders", "telegram_id", "order_date", "price_with_disc", args.user_id, args.date_from, args.date_to)
        advertising = _table_stats(cur, "advertising", "telegram_id", "advert_date", "spend", args.user_id, args.date_from, args.date_to)
        finance_raw = _table_stats(
            cur,
            "finance_raw_audit",
            "telegram_id",
            "report_date",
            "ABS(COALESCE(deduction,0))+ABS(COALESCE(acquiring_fee,0))+ABS(COALESCE(penalty,0))+ABS(COALESCE(acceptance,0))+ABS(COALESCE(acceptance_fee,0))+ABS(COALESCE(additional_payment,0))",
            args.user_id,
            args.date_from,
            args.date_to,
        )
    finally:
        conn.close()

    integrity = build_finance_source_integrity_report(args.user_id, args.date_from, args.date_to, autoload=True)
    snapshot = build_unified_financial_snapshot_dict(args.user_id, (args.date_from, args.date_to))

    print(f"DB: {DB_NAME}")
    print(f"user_id: {args.user_id}")
    print(f"period: {args.date_from}..{args.date_to}")

    _print_layer("Sales", sales)
    _print_layer("Orders", orders)
    _print_layer("Advertising", advertising)
    _print_layer("Finance Raw", finance_raw)

    _print_section("Expense Events")
    print(f"Rows: {int(integrity.get('rows_total') or 0)}")
    categories = dict(integrity.get("categories") or {})
    for name in ("advertising", "logistics", "storage", "acquiring", "wb_deductions", "penalties", "other"):
        item = dict(categories.get(name) or {})
        print(
            f"{name}: amount {_money(item.get('amount'))} | rows {int(item.get('rows') or 0)} | "
            f"docs {int(item.get('unique_documents') or 0)} | dates {item.get('min_date') or '-'}..{item.get('max_date') or '-'} | "
            f"source_tables {','.join(item.get('source_tables') or []) or '-'} | source_types {','.join(item.get('source_types') or []) or '-'} | "
            f"statuses {','.join(item.get('finance_statuses') or []) or '-'} | traceable {'yes' if item.get('traceable') else 'no'}"
        )

    _print_section("Snapshot")
    print(f"Revenue: {_money(snapshot.get('sales_revenue'))}")
    print(f"Expenses Total: {_money(snapshot.get('expenses_total'))}")
    print(f"Net Profit: {_money(snapshot.get('net_profit'))}")
    print(f"Finance Status: {snapshot.get('finance_status')}")

    _print_section("Finance Raw vs Expense Events")
    mismatches = list(integrity.get("mismatches") or [])
    accepted_warnings = list(integrity.get("accepted_warnings") or [])
    if mismatches:
        for item in mismatches:
            print(
                f"{item.get('category')}: finance_raw_audit={_money(item.get('finance_raw_audit'))} | "
                f"finance_expense_events={_money(item.get('finance_expense_events'))}"
            )
    else:
        for name, values in dict(integrity.get("finance_raw_to_events") or {}).items():
            print(
                f"{name}: finance_raw_audit={_money(values.get('finance_raw_audit'))} | "
                f"finance_expense_events={_money(values.get('finance_expense_events'))}"
            )

    _print_section("Accepted Warnings")
    if accepted_warnings:
        for item in accepted_warnings:
            print(
                f"{item.get('category')}: finance_raw_audit={_money(item.get('finance_raw_audit'))} | "
                f"finance_expense_events={_money(item.get('finance_expense_events'))} | reason={item.get('reason') or '-'}"
            )
    else:
        print("none")

    _print_section("Duplicates")
    duplicates = list(integrity.get("duplicates") or [])
    if duplicates:
        for item in duplicates[:20]:
            print(
                f"{item.get('expense_category')} | {item.get('source_event_id')} | {item.get('event_date')} | "
                f"{_money(item.get('amount'))} | dup_rows {int(item.get('duplicate_rows') or 0)}"
            )
    else:
        print("none")

    _print_section("Out-of-period Rows")
    out_of_period = list(integrity.get("out_of_period_rows") or [])
    if out_of_period:
        for item in out_of_period[:100]:
            print(
                f"{item.get('expense_category')} | {item.get('source_event_id')} | "
                f"event_date={item.get('event_date')} | period_key={item.get('period_key')} | amount={_money(item.get('amount'))}"
            )
    else:
        print("none")

    _print_section("Source Integrity")
    print(f"PASS / FAIL: {integrity.get('status')}")

    if args.trace_category:
        _print_section(f"Trace Category: {args.trace_category}")
        trace_rows = get_finance_expense_event_trace(args.user_id, args.date_from, args.date_to, args.trace_category, limit=100)
        if trace_rows:
            for item in trace_rows:
                print(f"event_id: {item.get('event_id')}")
                print(f"amount: {_money(item.get('amount'))}")
                print(f"event_date: {item.get('event_date') or '-'}")
                print(f"source: {item.get('source_type') or '-'}")
                print(f"source_table: {item.get('source_table') or '-'}")
                print(f"source_id: {item.get('source_id') or '-'}")
                print(f"source_hash: {item.get('source_hash') or '-'}")
                print(f"confidence: {item.get('confidence') or '-'}")
                print(f"status: {item.get('status') or '-'}")
                print(f"created_at: {item.get('created_at') or '-'}")
                print()
        else:
            print("none")

    return 0 if str(integrity.get("status")) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
