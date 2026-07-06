from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
import telegram_bot
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict
from vooglii_telegram.services.token_resolver import resolve_wb_token


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def _print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _fetchall(cur: sqlite3.Cursor, query: str, params: Iterable[object] = ()) -> list[tuple]:
    cur.execute(query, tuple(params))
    return list(cur.fetchall())


def _fetchone(cur: sqlite3.Cursor, query: str, params: Iterable[object] = ()) -> tuple:
    cur.execute(query, tuple(params))
    row = cur.fetchone()
    return tuple(row) if row is not None else tuple()


def _table_summary(cur: sqlite3.Cursor, table: str, user_id: int, date_col: str, amount_exprs: list[tuple[str, str]]) -> dict[str, object]:
    select_parts = [
        "COUNT(*)",
        f"MIN(substr({date_col},1,10))",
        f"MAX(substr({date_col},1,10))",
    ]
    select_parts.extend([f"COALESCE(SUM({expr}),0)" for _, expr in amount_exprs])
    global_query = f"SELECT {', '.join(select_parts)} FROM {table} WHERE substr({date_col},1,10) BETWEEN ? AND ?"
    user_query = global_query + " AND telegram_id=?"
    global_row = _fetchone(cur, global_query, (ARGS.date_from, ARGS.date_to))
    user_row = _fetchone(cur, user_query, (ARGS.date_from, ARGS.date_to, user_id))
    user_distribution = _fetchall(
        cur,
        f"""
        SELECT telegram_id, COUNT(*) AS rows_count
        FROM {table}
        WHERE substr({date_col},1,10) BETWEEN ? AND ?
        GROUP BY telegram_id
        ORDER BY rows_count DESC, telegram_id ASC
        LIMIT 10
        """,
        (ARGS.date_from, ARGS.date_to),
    )
    payload = {
        "global": global_row,
        "user": user_row,
        "distribution": user_distribution,
        "amount_labels": [label for label, _ in amount_exprs],
    }
    return payload


def _print_table_summary(name: str, summary: dict[str, object]) -> None:
    global_row = list(summary["global"])
    user_row = list(summary["user"])
    amount_labels = list(summary["amount_labels"])
    print(name)
    if global_row:
        print(f"  global rows: {int(global_row[0] or 0)} | dates: {global_row[1] or '-'} .. {global_row[2] or '-'}")
        for idx, label in enumerate(amount_labels, start=3):
            print(f"  global {label}: {_money(global_row[idx] or 0)}")
    if user_row:
        print(f"  user rows: {int(user_row[0] or 0)} | dates: {user_row[1] or '-'} .. {user_row[2] or '-'}")
        for idx, label in enumerate(amount_labels, start=3):
            print(f"  user {label}: {_money(user_row[idx] or 0)}")
    distribution = list(summary["distribution"] or [])
    if distribution:
        print("  user_id distribution:")
        for telegram_id, rows_count in distribution:
            print(f"    {telegram_id}: {rows_count}")


def _print_unmatched_costs(cur: sqlite3.Cursor, user_id: int) -> None:
    rows = _fetchall(
        cur,
        """
        SELECT
            TRIM(COALESCE(s.supplier_article, '')) AS supplier_article,
            COUNT(*) AS rows_count,
            COALESCE(SUM(s.price_with_disc),0) AS revenue_total,
            COALESCE(SUM(s.for_pay),0) AS payout_total
        FROM sales s
        WHERE s.telegram_id=?
          AND substr(s.sale_date,1,10) BETWEEN ? AND ?
          AND TRIM(COALESCE(s.supplier_article, ''))!=''
          AND COALESCE((
                SELECT p2.cost_price
                FROM products p2
                WHERE p2.supplier_article=s.supplier_article
                  AND p2.telegram_id IN (s.telegram_id, 0)
                ORDER BY p2.telegram_id DESC
                LIMIT 1
          ), 0) <= 0
        GROUP BY TRIM(COALESCE(s.supplier_article, ''))
        ORDER BY payout_total DESC, rows_count DESC, supplier_article ASC
        LIMIT 10
        """,
        (user_id, ARGS.date_from, ARGS.date_to),
    )
    if not rows:
        print("No unmatched sales SKU for cost mapping.")
        return
    for article, rows_count, revenue_total, payout_total in rows:
        print(f"{article or '-'} | rows {rows_count} | revenue {_money(revenue_total)} | payout {_money(payout_total)}")


def _print_products_summary(cur: sqlite3.Cursor, user_id: int) -> None:
    rows = _fetchall(
        cur,
        """
        SELECT telegram_id, COUNT(*), COALESCE(SUM(CASE WHEN COALESCE(cost_price,0)>0 THEN 1 ELSE 0 END),0)
        FROM products
        GROUP BY telegram_id
        ORDER BY COUNT(*) DESC, telegram_id ASC
        """,
    )
    if not rows:
        print("products table is empty.")
        return
    for telegram_id, total_rows, rows_with_cost in rows:
        marker = " <target>" if int(telegram_id or 0) == int(user_id) else ""
        print(f"{telegram_id}{marker} | rows {total_rows} | with cost {rows_with_cost}")


def _print_cost_matching_diagnostics(cur: sqlite3.Cursor, user_id: int) -> None:
    sales_row = _fetchone(
        cur,
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(CASE WHEN nm_id IS NOT NULL AND TRIM(CAST(nm_id AS TEXT))!='' AND TRIM(CAST(nm_id AS TEXT))!='0' THEN 1 ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN TRIM(COALESCE(supplier_article,''))!='' THEN 1 ELSE 0 END),0),
            COUNT(DISTINCT CASE WHEN nm_id IS NOT NULL AND TRIM(CAST(nm_id AS TEXT))!='' AND TRIM(CAST(nm_id AS TEXT))!='0' THEN CAST(nm_id AS TEXT) END),
            COUNT(DISTINCT CASE WHEN TRIM(COALESCE(supplier_article,''))!='' THEN TRIM(supplier_article) END)
        FROM sales
        WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?
        """,
        (user_id, ARGS.date_from, ARGS.date_to),
    )
    print(f"sales rows: {int((sales_row or [0])[0] or 0)}")
    print(f"sales rows with nm_id: {int((sales_row or [0] * 5)[1] or 0)}")
    print(f"sales rows with supplier_article: {int((sales_row or [0] * 5)[2] or 0)}")
    print(f"distinct nm_id in sales: {int((sales_row or [0] * 5)[3] or 0)}")
    print(f"distinct supplier_article in sales: {int((sales_row or [0] * 5)[4] or 0)}")

    product_row = _fetchone(
        cur,
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(CASE WHEN COALESCE(cost_price,0)>0 THEN 1 ELSE 0 END),0),
            COUNT(DISTINCT CASE WHEN TRIM(COALESCE(supplier_article,''))!='' THEN TRIM(supplier_article) END)
        FROM products
        WHERE telegram_id IN (?, 0)
        """,
        (user_id,),
    )
    print(f"products rows user+global: {int((product_row or [0])[0] or 0)}")
    print(f"products rows with cost user+global: {int((product_row or [0] * 3)[1] or 0)}")
    print(f"distinct supplier_article in products user+global: {int((product_row or [0] * 3)[2] or 0)}")

    unmatched_rows = _fetchall(
        cur,
        """
        SELECT
            COALESCE(NULLIF(TRIM(s.supplier_article), ''), '[no article]') AS article_key,
            COALESCE(NULLIF(TRIM(CAST(s.nm_id AS TEXT)), ''), '[no nm_id]') AS nm_key,
            COUNT(*) AS rows_count,
            COALESCE(SUM(s.for_pay),0) AS payout_total
        FROM sales s
        WHERE s.telegram_id=?
          AND substr(s.sale_date,1,10) BETWEEN ? AND ?
          AND COALESCE((
                SELECT p2.cost_price
                FROM products p2
                WHERE p2.supplier_article=s.supplier_article
                  AND p2.telegram_id IN (s.telegram_id, 0)
                ORDER BY p2.telegram_id DESC
                LIMIT 1
          ), 0) <= 0
        GROUP BY article_key, nm_key
        ORDER BY payout_total DESC, rows_count DESC, article_key ASC
        LIMIT 10
        """,
        (user_id, ARGS.date_from, ARGS.date_to),
    )
    if unmatched_rows:
        print("top unmatched SKU:")
        for article_key, nm_key, rows_count, payout_total in unmatched_rows:
            print(f"  article={article_key} | nm_id={nm_key} | rows={rows_count} | payout={_money(payout_total)}")
    else:
        print("top unmatched SKU: none")


def _print_finance_breakdown(cur: sqlite3.Cursor, user_id: int) -> None:
    row = _fetchone(
        cur,
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(ABS(COALESCE(acquiring_fee,0))),0),
            COALESCE(SUM(ABS(COALESCE(deduction,0))),0),
            COALESCE(SUM(ABS(COALESCE(penalty,0))),0),
            COALESCE(SUM(ABS(COALESCE(acceptance,0))),0),
            COALESCE(SUM(ABS(COALESCE(acceptance_fee,0))),0),
            COALESCE(SUM(ABS(COALESCE(additional_payment,0))),0)
        FROM finance_raw_audit
        WHERE telegram_id=?
          AND substr(report_date,1,10) BETWEEN ? AND ?
        """,
        (user_id, ARGS.date_from, ARGS.date_to),
    )
    print(f"rows: {int((row or [0])[0] or 0)}")
    print(f"acquiring: {_money((row or [0] * 7)[1] or 0)}")
    print(f"deductions: {_money((row or [0] * 7)[2] or 0)}")
    print(f"penalties: {_money((row or [0] * 7)[3] or 0)}")
    print(f"acceptance: {_money((row or [0] * 7)[4] or 0)}")
    print(f"acceptance_fee: {_money((row or [0] * 7)[5] or 0)}")
    print(f"additional_payment: {_money((row or [0] * 7)[6] or 0)}")


def _customer_renderer_fields(unified: dict[str, object]) -> dict[str, dict[str, object]]:
    report_fields = {
        "revenue": unified.get("sales_revenue"),
        "advertising": unified.get("advertising_spend"),
        "logistics": unified.get("logistics"),
        "storage": unified.get("storage"),
        "acquiring": unified.get("acquiring"),
        "wb_deductions": unified.get("wb_deductions"),
        "other_expenses": unified.get("other_expenses"),
        "unknown_wb_expenses": unified.get("customer_unknown_wb_expenses"),
        "reconciliation_delta": unified.get("reconciliation_delta"),
        "expenses_total": unified.get("expenses_total"),
        "profit_before_tax": unified.get("profit_before_tax"),
        "net_profit": unified.get("net_profit"),
        "finance_status": unified.get("finance_status"),
        "ads_status": unified.get("advertising_status"),
        "cost_status": unified.get("cost_status"),
    }
    finance_fields = {
        "wb_payout": unified.get("wb_payout"),
        "payments_received": unified.get("wb_payments_received"),
        "advertising": unified.get("advertising_spend"),
        "cost_price": unified.get("cost_price"),
        "logistics": unified.get("logistics"),
        "storage": unified.get("storage"),
        "acquiring": unified.get("acquiring"),
        "wb_deductions": unified.get("wb_deductions"),
        "other_expenses": unified.get("other_expenses"),
        "unknown_wb_expenses": unified.get("customer_unknown_wb_expenses"),
        "reconciliation_delta": unified.get("reconciliation_delta"),
        "expenses_total": unified.get("expenses_total"),
        "profit": unified.get("net_profit"),
        "finance_status": unified.get("finance_status"),
        "cost_status": unified.get("cost_status"),
    }
    pnl_fields = {
        "revenue": unified.get("sales_revenue"),
        "advertising": unified.get("advertising_spend"),
        "logistics": unified.get("logistics"),
        "cost_price": unified.get("cost_price"),
        "expenses_total": unified.get("expenses_total"),
        "profit": unified.get("net_profit"),
        "profit_before_tax": unified.get("profit_before_tax"),
        "margin_percent": unified.get("margin_percent"),
        "finance_status": unified.get("finance_status"),
        "cost_status": unified.get("cost_status"),
    }
    return {"report": report_fields, "finance": finance_fields, "pnl": pnl_fields}


def _print_mapping(title: str, payload: dict[str, object]) -> None:
    _print_section(title)
    for key, value in payload.items():
        print(f"{key}: {value}")


def _print_runtime_snapshots(user_id: int) -> None:
    days = (ARGS.date_from, ARGS.date_to)
    request_context = telegram_bot._snapshot_context()
    unified = build_unified_financial_snapshot_dict(user_id, days, context=request_context, bot=telegram_bot._unified_finance_bot())
    mgmt = telegram_bot._report_mgmt_snapshot(user_id, days)
    finance = telegram_bot.get_finance_difference_snapshot(user_id, ARGS.date_from, ARGS.date_to)
    payment = telegram_bot._payment_reconciliation_snapshot(user_id, ARGS.date_from, ARGS.date_to)
    profit_audit = telegram_bot._profit_audit_snapshot(user_id, days)
    renderer_fields = _customer_renderer_fields(unified)
    sources = dict(unified.get("debug_sources") or {})

    _print_section("Unified Snapshot")
    for key in (
        "sales_revenue",
        "wb_payout",
        "cost_price",
        "advertising_spend",
        "logistics",
        "storage",
        "acquiring",
        "wb_deductions",
        "other_expenses",
        "unknown_wb_expenses",
        "reconciliation_delta",
        "expenses_total",
        "profit_before_tax",
        "tax_amount",
        "net_profit",
        "finance_status",
        "advertising_status",
        "cost_status",
    ):
        print(f"{key}: {unified.get(key)}")

    _print_mapping("Unified Snapshot Sources", sources)

    _print_section("Report Mgmt Snapshot")
    for key in ("revenue", "payout", "cost_price", "advertising", "logistics", "storage", "acquiring", "deductions", "other", "unexplained"):
        print(f"{key}: {mgmt.get(key)}")

    _print_section("Finance Difference Snapshot")
    for key in ("status", "coverage_percent", "logistics", "storage", "acquiring", "deductions", "explicit_other_deductions", "other_deductions", "residual_other_deductions"):
        print(f"{key}: {finance.get(key)}")

    _print_section("Payment Reconciliation Snapshot")
    for key in ("payment_reports_source", "payment_reports_status", "payment_reports_count", "sales_revenue_total", "sales_for_pay_total", "weekly_payout_total_all", "payment_reports_total_delivery", "payment_reports_total_storage", "payment_reports_total_deduction"):
        print(f"{key}: {payment.get(key)}")

    _print_section("Profit Audit Components")
    components = (profit_audit.get("profit_reconciliation_debug") or {}).get("components") or {}
    for key, value in components.items():
        print(f"{key}: {value}")

    _print_mapping("Report Renderer Fields", renderer_fields["report"])
    _print_mapping("Finance Renderer Fields", renderer_fields["finance"])
    _print_mapping("P&L Renderer Fields", renderer_fields["pnl"])

    _print_section("Status Sources")
    print(f"finance_status source: {((sources.get('finance_status') or {}).get('selected_source'))}")
    print(f"ads_status source: {((sources.get('advertising_status') or {}).get('selected_source'))}")
    print(f"cost_status source: {((sources.get('cost_status') or {}).get('selected_source'))}")

    _print_section("Advertising Source Selection")
    advertising_table_total = _money((telegram_bot._advertising_customer_snapshot(user_id, days) or {}).get("total_spend"))
    expenses_rows = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        expenses_rows = _fetchone(
            cur,
            """
            SELECT COALESCE(SUM(amount),0)
            FROM expenses
            WHERE telegram_id=?
              AND substr(expense_date,1,10) BETWEEN ? AND ?
              AND lower(COALESCE(expense_type,''))='advertising'
            """,
            (user_id, ARGS.date_from, ARGS.date_to),
        )
        conn.close()
    except Exception:
        expenses_rows = (0.0,)
    print(f"advertising table total: {advertising_table_total}")
    print(f"expenses advertising total: {_money((expenses_rows or [0])[0] or 0)}")
    print(f"ads health total: {_money((telegram_bot._advertising_customer_snapshot(user_id, days) or {}).get('total_spend'))}")
    print(f"selected source: {((sources.get('advertising_spend') or {}).get('selected_source'))}")

    _print_section("Customer Outputs")
    print("/report")
    print(telegram_bot._unified_report_text(user_id, days))
    print()
    print("/finance")
    print(telegram_bot._finance_center_text(user_id, days))
    print()
    print("/pnl")
    print(telegram_bot._pnl_customer_text(user_id, days))


def main() -> None:
    user_id = int(ARGS.user_id)
    print(f"DB: {DB_NAME}")
    print(f"user_id: {user_id}")
    print(f"period: {ARGS.date_from}..{ARGS.date_to}")

    token_resolution = resolve_wb_token(user_id)
    _print_section("WB Token Resolution")
    print(f"status: {token_resolution.status}")
    print(f"source: {token_resolution.source}")
    print(f"token_len: {token_resolution.token_len}")
    print(f"encrypted: {token_resolution.encrypted}")
    print(f"can_decrypt: {token_resolution.can_decrypt}")
    if token_resolution.reason:
        print(f"reason: {token_resolution.reason}")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        _print_section("Table Counts")
        table_specs = {
            "sales": ("sale_date", [("total_price", "total_price"), ("for_pay", "for_pay"), ("price_with_disc", "price_with_disc")]),
            "orders": ("order_date", [("total_price", "total_price"), ("price_with_disc", "price_with_disc")]),
            "advertising": ("advert_date", [("spend", "spend"), ("sum_price", "sum_price")]),
            "expenses": ("expense_date", [("amount", "amount")]),
            "finance_raw_audit": ("report_date", [("deduction_abs", "ABS(COALESCE(deduction,0))"), ("acquiring_abs", "ABS(COALESCE(acquiring_fee,0))"), ("other_abs", "ABS(COALESCE(penalty,0))+ABS(COALESCE(acceptance,0))+ABS(COALESCE(acceptance_fee,0))+ABS(COALESCE(additional_payment,0))")]),
            "stocks": ("stock_date", []),
        }
        for table_name, (date_col, amount_exprs) in table_specs.items():
            _print_table_summary(table_name, _table_summary(cur, table_name, user_id, date_col, amount_exprs))

        _print_section("Products")
        _print_products_summary(cur, user_id)

        _print_section("Top Unmatched Cost SKU")
        _print_unmatched_costs(cur, user_id)

        _print_section("Cost Matching Diagnostics")
        _print_cost_matching_diagnostics(cur, user_id)

        _print_section("Expense Type Breakdown")
        rows = _fetchall(
            cur,
            """
            SELECT expense_type, COUNT(*), COALESCE(SUM(amount),0)
            FROM expenses
            WHERE telegram_id=? AND substr(expense_date,1,10) BETWEEN ? AND ?
            GROUP BY expense_type
            ORDER BY SUM(amount) DESC, expense_type ASC
            """,
            (user_id, ARGS.date_from, ARGS.date_to),
        )
        if rows:
            for expense_type, rows_count, total_amount in rows:
                print(f"{expense_type}: rows {rows_count} | amount {_money(total_amount)}")
        else:
            print("No expense rows in period.")

        _print_section("Finance Raw Breakdown")
        _print_finance_breakdown(cur, user_id)
    finally:
        conn.close()

    _print_runtime_snapshots(user_id)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Diagnose financial source data for a period.")
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    ARGS = parser.parse_args()
    main()
