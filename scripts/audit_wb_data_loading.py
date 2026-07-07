from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
from product_catalog import build_product_catalog_audit


BLOCKS = ("sales", "orders", "advertising", "finance", "stocks", "products", "cost")


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _money(value: Any) -> str:
    try:
        return f"{float(value or 0):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def _parse_meta(raw_value: Any) -> dict[str, Any]:
    text = str(raw_value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {"raw_meta": text}
    return payload if isinstance(payload, dict) else {"raw_meta": payload}


def _period_days(date_from: str, date_to: str) -> int:
    start_dt = datetime.strptime(str(date_from), "%Y-%m-%d")
    end_dt = datetime.strptime(str(date_to), "%Y-%m-%d")
    return max(1, (end_dt - start_dt).days + 1)


def _rolling_start(days: int) -> str:
    return (datetime.now() - timedelta(days=max(1, int(days)) - 1)).strftime("%Y-%m-%d")


def _table_stats(
    conn: sqlite3.Connection,
    table: str,
    user_column: str,
    date_column: str,
    amount_expr: str | None,
    user_id: int,
    date_from: str,
    date_to: str,
) -> dict[str, Any]:
    select_amount = f", ROUND(COALESCE(SUM({amount_expr}),0),2) AS total_amount" if amount_expr else ""
    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            MIN(substr({date_column},1,10)) AS min_date,
            MAX(substr({date_column},1,10)) AS max_date
            {select_amount}
        FROM {table}
        WHERE {user_column}=?
          AND substr({date_column},1,10) BETWEEN ? AND ?
        """,
        (int(user_id), str(date_from), str(date_to)),
    ).fetchone()
    return dict(row or {})


def _all_user_distribution(
    conn: sqlite3.Connection,
    table: str,
    user_column: str,
    date_column: str | None,
    amount_expr: str,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    if date_column:
        query = f"""
            SELECT
                {user_column} AS user_id,
                COUNT(*) AS rows_count,
                ROUND(COALESCE(SUM(COALESCE({amount_expr},0)),0),2) AS total_amount
            FROM {table}
            WHERE substr({date_column},1,10) BETWEEN ? AND ?
            GROUP BY {user_column}
            ORDER BY rows_count DESC, total_amount DESC, {user_column}
        """
        params = (str(date_from), str(date_to))
    else:
        query = f"""
            SELECT
                {user_column} AS user_id,
                COUNT(*) AS rows_count,
                ROUND(COALESCE(SUM(COALESCE({amount_expr},0)),0),2) AS total_amount
            FROM {table}
            GROUP BY {user_column}
            ORDER BY rows_count DESC, total_amount DESC, {user_column}
        """
        params = ()
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _extract_sync_period(meta: dict[str, Any]) -> tuple[str | None, str | None]:
    period_from = meta.get("range_start") or meta.get("period_begin") or meta.get("date_from")
    period_to = meta.get("range_end") or meta.get("period_end") or meta.get("date_to")
    return period_from, period_to


def _sync_state_snapshot(conn: sqlite3.Connection, user_id: int) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM sync_state WHERE telegram_id=? ORDER BY sync_block",
        (int(user_id),),
    ).fetchall()
    by_block: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        meta = _parse_meta(item.get("meta_json"))
        period_from, period_to = _extract_sync_period(meta)
        by_block[str(item["sync_block"])] = {
            "status": item.get("status"),
            "period_from": period_from,
            "period_to": period_to,
            "rows_inserted": int(item.get("rows_inserted") or 0),
            "rows_updated": int(item.get("rows_updated") or 0),
            "rows_skipped": int(item.get("rows_skipped") or 0),
            "last_success_at": item.get("last_success_at"),
            "error": item.get("status_reason"),
            "next_allowed_at": item.get("next_allowed_at"),
            "source_rows": int(item.get("source_rows") or 0),
            "source_name": item.get("source_name"),
            "meta": meta,
        }
    return by_block


def _cost_audit(conn: sqlite3.Connection, user_id: int, date_from: str, date_to: str) -> dict[str, Any]:
    audit = build_product_catalog_audit(int(user_id), period=(str(date_from), str(date_to)))
    return {
        "catalog_rows": int(audit.get("catalog_rows") or 0),
        "catalog_rows_with_cost": int(audit.get("rows_with_cost") or 0),
        "catalog_rows_without_cost": int(audit.get("rows_without_cost") or 0),
        "total_sales_rows": int(audit.get("sales_rows") or 0),
        "rows_with_cost": int(audit.get("matched_sales_rows") or 0),
        "coverage_percent": float(audit.get("coverage_percent") or 0),
        "matched_by_nm_id": int(audit.get("matched_by_nm_id") or 0),
        "matched_by_supplier_article": int(audit.get("matched_by_supplier_article") or 0),
        "matched_by_barcode": int(audit.get("matched_by_barcode") or 0),
        "matched_by_legacy_fallback": int(audit.get("matched_by_legacy_fallback") or 0),
        "legacy_products_rows": int(audit.get("legacy_products_rows") or 0),
        "legacy_products_rows_with_cost": int(audit.get("legacy_products_rows_with_cost") or 0),
        "top_unmatched_sku": [dict(row) for row in list(audit.get("top_missing_cost") or [])],
    }


def _finance_categories(conn: sqlite3.Connection, user_id: int, date_from: str, date_to: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            expense_category,
            COUNT(*) AS rows_count,
            ROUND(COALESCE(SUM(amount),0),2) AS total_amount,
            MIN(substr(event_date,1,10)) AS min_date,
            MAX(substr(event_date,1,10)) AS max_date,
            GROUP_CONCAT(DISTINCT COALESCE(source_table,'')) AS source_tables
        FROM finance_expense_events
        WHERE user_id=?
          AND substr(event_date,1,10) BETWEEN ? AND ?
        GROUP BY expense_category
        ORDER BY expense_category
        """,
        (int(user_id), str(date_from), str(date_to)),
    ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        item["source_tables"] = [part for part in str(item.get("source_tables") or "").split(",") if part]
        result[str(item["expense_category"])] = item
    return result


def _period_window_mismatch(conn: sqlite3.Connection, user_id: int, date_from: str, date_to: str) -> dict[str, Any]:
    days = _period_days(date_from, date_to)
    rolling_from = _rolling_start(days)
    sales_period = _table_stats(conn, "sales", "telegram_id", "sale_date", "price_with_disc", user_id, date_from, date_to)
    sales_rolling = _table_stats(conn, "sales", "telegram_id", "sale_date", "price_with_disc", user_id, rolling_from, datetime.now().strftime("%Y-%m-%d"))
    advertising_period = _table_stats(conn, "advertising", "telegram_id", "advert_date", "spend", user_id, date_from, date_to)
    advertising_rolling = _table_stats(conn, "advertising", "telegram_id", "advert_date", "spend", user_id, rolling_from, datetime.now().strftime("%Y-%m-%d"))
    return {
        "period_days": days,
        "rolling_window_from": rolling_from,
        "rolling_window_to": datetime.now().strftime("%Y-%m-%d"),
        "sales_period_rows": int(sales_period.get("rows_count") or 0),
        "sales_rolling_rows": int(sales_rolling.get("rows_count") or 0),
        "advertising_period_rows": int(advertising_period.get("rows_count") or 0),
        "advertising_rolling_rows": int(advertising_rolling.get("rows_count") or 0),
    }


def build_wb_data_loading_audit(user_id: int, date_from: str, date_to: str, db_path: str | None = None) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "user_id": int(user_id),
        "date_from": str(date_from),
        "date_to": str(date_to),
        "db_path": db_path or DB_NAME,
        "sync_state": {},
        "tables": {},
        "user_distribution": {},
        "finance_categories": {},
        "cost_audit": {},
        "period_window_check": {},
        "conclusions": [],
    }
    conn = _connect(db_path)
    try:
        sync_state = _sync_state_snapshot(conn, user_id)
        audit["sync_state"] = {}
        for block in BLOCKS:
            audit["sync_state"][block] = sync_state.get(
                block,
                {
                    "status": "MISSING",
                    "period_from": None,
                    "period_to": None,
                    "rows_inserted": 0,
                    "rows_updated": 0,
                    "rows_skipped": 0,
                    "last_success_at": None,
                    "error": "sync_state row not found",
                    "next_allowed_at": None,
                    "source_rows": 0,
                    "source_name": None,
                    "meta": {},
                },
            )

        audit["tables"] = {
            "sales": _table_stats(conn, "sales", "telegram_id", "sale_date", "price_with_disc", user_id, date_from, date_to),
            "orders": _table_stats(conn, "orders", "telegram_id", "order_date", "price_with_disc", user_id, date_from, date_to),
            "advertising": _table_stats(conn, "advertising", "telegram_id", "advert_date", "spend", user_id, date_from, date_to),
            "expenses": _table_stats(conn, "expenses", "telegram_id", "expense_date", "amount", user_id, date_from, date_to),
            "finance_raw_audit": _table_stats(conn, "finance_raw_audit", "telegram_id", "report_date", None, user_id, date_from, date_to),
            "finance_expense_events": _table_stats(conn, "finance_expense_events", "user_id", "event_date", "amount", user_id, date_from, date_to),
            "stocks": _table_stats(conn, "stocks", "telegram_id", "stock_date", "quantity", user_id, date_from, date_to),
        }
        audit["cost_audit"] = _cost_audit(conn, user_id, date_from, date_to)
        audit["products"] = {
            "rows_count": int(audit["cost_audit"].get("catalog_rows") or 0),
            "rows_with_cost": int(audit["cost_audit"].get("catalog_rows_with_cost") or 0),
            "rows_without_cost": int(audit["cost_audit"].get("catalog_rows_without_cost") or 0),
            "legacy_rows_count": int(audit["cost_audit"].get("legacy_products_rows") or 0),
            "legacy_rows_with_cost": int(audit["cost_audit"].get("legacy_products_rows_with_cost") or 0),
        }
        audit["user_distribution"] = {
            "sales": _all_user_distribution(conn, "sales", "telegram_id", "sale_date", "price_with_disc", date_from, date_to),
            "orders": _all_user_distribution(conn, "orders", "telegram_id", "order_date", "price_with_disc", date_from, date_to),
            "advertising": _all_user_distribution(conn, "advertising", "telegram_id", "advert_date", "spend", date_from, date_to),
            "expenses": _all_user_distribution(conn, "expenses", "telegram_id", "expense_date", "amount", date_from, date_to),
            "finance_raw_audit": _all_user_distribution(conn, "finance_raw_audit", "telegram_id", "report_date", "deduction", date_from, date_to),
            "product_catalog": _all_user_distribution(conn, "product_catalog", "user_id", None, "cost_price", date_from, date_to),
            "legacy_products": _all_user_distribution(conn, "products", "telegram_id", None, "cost_price", date_from, date_to),
            "stocks": _all_user_distribution(conn, "stocks", "telegram_id", "stock_date", "quantity", date_from, date_to),
            "finance_expense_events": _all_user_distribution(conn, "finance_expense_events", "user_id", "event_date", "amount", date_from, date_to),
        }
        audit["finance_categories"] = _finance_categories(conn, user_id, date_from, date_to)
        audit["period_window_check"] = _period_window_mismatch(conn, user_id, date_from, date_to)

        conclusions: list[str] = []
        if all(item["status"] == "MISSING" for item in audit["sync_state"].values()):
            conclusions.append("sync_state is empty for all blocks, so last successful loader runs are not persisted for this user")
        sales_rows = int(audit["tables"]["sales"].get("rows_count") or 0)
        orders_rows = int(audit["tables"]["orders"].get("rows_count") or 0)
        if sales_rows > 0 and audit["period_window_check"]["sales_rolling_rows"] == 0:
            conclusions.append("period-aware May data exists in the DB, but a rolling last-N-days query would return zero from the current date")
        finance_events_rows = int(audit["tables"]["finance_expense_events"].get("rows_count") or 0)
        if finance_events_rows > max(sales_rows, orders_rows):
            conclusions.append("finance_expense_events is wider because it normalizes advertising + expenses + finance_raw_audit into one layer")
        advertising_rows = int(audit["tables"]["advertising"].get("rows_count") or 0)
        advertising_category = audit["finance_categories"].get("advertising") or {}
        if advertising_rows == 0:
            conclusions.append("advertising table is empty for the period, so any advertising amount must come from a fallback source")
        elif int(advertising_category.get("rows_count") or 0) == 0:
            conclusions.append("advertising table has rows, but finance_expense_events has no advertising rows, so the normalized layer is incomplete")
        if int(audit["cost_audit"].get("rows_with_cost") or 0) == 0 and sales_rows > 0:
            conclusions.append("sales rows exist but none of them map to a positive cost_price in product_catalog")
        elif sales_rows > 0 and int(audit["cost_audit"].get("rows_with_cost") or 0) == sales_rows:
            conclusions.append("all sales rows in the requested period map to product_catalog rows with positive cost_price")
        raw_min_date = audit["tables"]["finance_raw_audit"].get("min_date")
        if raw_min_date and str(raw_min_date) > str(date_from):
            conclusions.append("finance_raw_audit starts later than the requested period start, so WB finance coverage is partial even inside May")
        audit["conclusions"] = conclusions
    finally:
        conn.close()
    return audit


def _print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _print_sync_state(audit: dict[str, Any]) -> None:
    _print_section("Sync State")
    for block in BLOCKS:
        item = audit["sync_state"][block]
        print(f"{block}:")
        print(f"  status={item['status']}")
        print(f"  period_from={item.get('period_from') or '-'}")
        print(f"  period_to={item.get('period_to') or '-'}")
        print(f"  rows_inserted={item['rows_inserted']}")
        print(f"  rows_updated={item['rows_updated']}")
        print(f"  rows_skipped={item['rows_skipped']}")
        print(f"  last_success_at={item.get('last_success_at') or '-'}")
        print(f"  error={item.get('error') or '-'}")
        print(f"  next_allowed_at={item.get('next_allowed_at') or '-'}")


def _print_api_block(name: str, sync_item: dict[str, Any], table_item: dict[str, Any], date_from: str, date_to: str) -> None:
    print(f"{name} API:")
    print(f"- requested date_from/date_to: {sync_item.get('period_from') or date_from} .. {sync_item.get('period_to') or date_to}")
    print(f"- response rows: {sync_item.get('source_rows') if sync_item.get('status') != 'MISSING' else 'unknown'}")
    print(f"- inserted rows: {sync_item.get('rows_inserted', 0)}")
    print(f"- skipped rows: {sync_item.get('rows_skipped', 0)}")
    print(f"- local table rows: {int(table_item.get('rows_count') or 0)}")
    print(f"- min/max dates: {table_item.get('min_date') or '-'} .. {table_item.get('max_date') or '-'}")
    print(f"- error: {sync_item.get('error') or '-'}")


def _print_report(audit: dict[str, Any]) -> None:
    print(f"user_id: {audit['user_id']}")
    print(f"db_path: {audit['db_path']}")
    print(f"period: {audit['date_from']}..{audit['date_to']}")
    _print_sync_state(audit)

    _print_section("API Loader Audit")
    _print_api_block("sales", audit["sync_state"]["sales"], audit["tables"]["sales"], audit["date_from"], audit["date_to"])
    _print_api_block("orders", audit["sync_state"]["orders"], audit["tables"]["orders"], audit["date_from"], audit["date_to"])
    _print_api_block("advertising", audit["sync_state"]["advertising"], audit["tables"]["advertising"], audit["date_from"], audit["date_to"])
    _print_api_block("finance", audit["sync_state"]["finance"], audit["tables"]["finance_raw_audit"], audit["date_from"], audit["date_to"])
    print("products/cost:")
    print(f"- product_catalog rows: {int(audit['products'].get('rows_count') or 0)}")
    print(f"- product_catalog rows_with_cost: {int(audit['products'].get('rows_with_cost') or 0)}")
    print(f"- product_catalog rows_without_cost: {int(audit['products'].get('rows_without_cost') or 0)}")
    print(f"- cost coverage in sales: {audit['cost_audit'].get('coverage_percent')}%")
    print(f"- matched by nm_id: {int(audit['cost_audit'].get('matched_by_nm_id') or 0)}")
    print(f"- matched by supplier_article: {int(audit['cost_audit'].get('matched_by_supplier_article') or 0)}")
    print(f"- matched by barcode: {int(audit['cost_audit'].get('matched_by_barcode') or 0)}")
    print(f"- legacy fallback matches: {int(audit['cost_audit'].get('matched_by_legacy_fallback') or 0)}")
    print(f"- legacy products fallback rows: {int(audit['products'].get('legacy_rows_count') or 0)}")
    print(f"- top unmatched sku count: {len(audit['cost_audit'].get('top_unmatched_sku') or [])}")

    _print_section("User ID Distribution")
    for table_name, rows in audit["user_distribution"].items():
        print(f"{table_name}:")
        if not rows:
            print("- none")
            continue
        for row in rows[:10]:
            print(
                f"- user_id={row['user_id']} rows={int(row['rows_count'] or 0)} amount={_money(row.get('total_amount'))}"
            )

    _print_section("Advertising")
    advertising_rows = audit["tables"]["advertising"]
    advertising_category = audit["finance_categories"].get("advertising") or {}
    print(f"table_rows={int(advertising_rows.get('rows_count') or 0)}")
    print(f"table_spend={_money(advertising_rows.get('total_amount'))}")
    print(f"normalized_rows={int(advertising_category.get('rows_count') or 0)}")
    print(f"normalized_spend={_money(advertising_category.get('total_amount'))}")
    print(f"normalized_sources={','.join(advertising_category.get('source_tables') or []) or '-'}")

    _print_section("Finance Expense Events")
    for category_name, item in audit["finance_categories"].items():
        print(
            f"- {category_name}: rows={int(item.get('rows_count') or 0)} amount={_money(item.get('total_amount'))} "
            f"dates={item.get('min_date') or '-'}..{item.get('max_date') or '-'} "
            f"sources={','.join(item.get('source_tables') or []) or '-'}"
        )

    _print_section("Cost Audit")
    print(f"total_sales_rows={audit['cost_audit']['total_sales_rows']}")
    print(f"rows_with_cost={audit['cost_audit']['rows_with_cost']}")
    print(f"coverage_percent={audit['cost_audit']['coverage_percent']}")
    print("top_unmatched_sku:")
    unmatched = audit["cost_audit"].get("top_unmatched_sku") or []
    if not unmatched:
        print("- none")
    else:
        for item in unmatched:
            print(
                f"- nm_id={item.get('nm_id') or '-'} supplierArticle={item.get('supplierArticle') or '-'} "
                f"barcode={item.get('barcode') or '-'} quantity={int(item.get('quantity') or 0)} "
                f"revenue={_money(item.get('revenue'))} reason={item.get('reason') or '-'}"
            )

    _print_section("Period Window Check")
    mismatch = audit["period_window_check"]
    print(
        f"period_days={mismatch['period_days']} rolling_window={mismatch['rolling_window_from']}..{mismatch['rolling_window_to']}"
    )
    print(
        f"sales_period_rows={mismatch['sales_period_rows']} sales_rolling_rows={mismatch['sales_rolling_rows']}"
    )
    print(
        f"advertising_period_rows={mismatch['advertising_period_rows']} advertising_rolling_rows={mismatch['advertising_rolling_rows']}"
    )

    _print_section("Conclusions")
    for item in audit.get("conclusions") or ["none"]:
        print(f"- {item}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()
    audit = build_wb_data_loading_audit(args.user_id, args.date_from, args.date_to)
    _print_report(audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
