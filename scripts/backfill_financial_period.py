from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
import db_manager
import load_sales
import telegram_bot


SOURCE_DB_CANDIDATES = [
    PROJECT_ROOT / "wildberries.db",
    PROJECT_ROOT / "backup" / "wildberries.db",
    PROJECT_ROOT / "storage" / "wildberries.backup.db",
]


def _money(value: Any) -> str:
    try:
        return f"{float(value or 0):,.2f}".replace(",", " ")
    except Exception:
        return str(value)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _table_summary(conn: sqlite3.Connection, table: str, date_col: str | None, user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
    cur = conn.cursor()
    if table == "sales":
        sums = "COALESCE(SUM(total_price),0), COALESCE(SUM(for_pay),0), COALESCE(SUM(price_with_disc),0)"
    elif table == "orders":
        sums = "COALESCE(SUM(total_price),0), COALESCE(SUM(price_with_disc),0)"
    elif table == "advertising":
        sums = "COALESCE(SUM(spend),0), COALESCE(SUM(sum_price),0)"
    elif table == "expenses":
        sums = "COALESCE(SUM(amount),0)"
    elif table == "finance_raw_audit":
        sums = (
            "COALESCE(SUM(ABS(COALESCE(deduction,0))),0), "
            "COALESCE(SUM(ABS(COALESCE(acquiring_fee,0))),0), "
            "COALESCE(SUM(ABS(COALESCE(penalty,0))+ABS(COALESCE(acceptance,0))+ABS(COALESCE(acceptance_fee,0))+ABS(COALESCE(additional_payment,0))),0)"
        )
    elif table == "products":
        cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN COALESCE(cost_price,0)>0 THEN 1 ELSE 0 END),0) "
            "FROM products WHERE telegram_id IN (?,0)",
            (user_id,),
        )
        row = cur.fetchone() or ()
        return {"rows": int(row[0] or 0), "metrics": [float(row[1] or 0)]}
    elif table == "stocks":
        sums = "0"
    else:
        sums = "0"

    if date_col:
        cur.execute(
            f"SELECT COUNT(*), {sums} FROM {table} WHERE telegram_id=? AND substr({date_col},1,10) BETWEEN ? AND ?",
            (user_id, start_date, end_date),
        )
    else:
        cur.execute(f"SELECT COUNT(*), {sums} FROM {table} WHERE telegram_id=?", (user_id,))
    row = cur.fetchone() or ()
    return {"rows": int(row[0] or 0), "metrics": [float(value or 0) for value in row[1:]]}


def _discover_source_db(user_id: int, start_date: str, end_date: str) -> tuple[Path | None, list[dict[str, Any]]]:
    discovered: list[dict[str, Any]] = []
    target_path = Path(DB_NAME).resolve()
    for candidate in SOURCE_DB_CANDIDATES:
        candidate = candidate.resolve()
        if not candidate.exists() or candidate == target_path:
            continue
        try:
            conn = _connect(candidate)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sales WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?", (user_id, start_date, end_date))
            sales_rows = int((cur.fetchone() or [0])[0] or 0)
            cur.execute("SELECT COUNT(*) FROM advertising WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?", (user_id, start_date, end_date))
            advertising_rows = int((cur.fetchone() or [0])[0] or 0)
            cur.execute("SELECT COUNT(*) FROM finance_raw_audit WHERE telegram_id=? AND substr(report_date,1,10) BETWEEN ? AND ?", (user_id, start_date, end_date))
            finance_rows = int((cur.fetchone() or [0])[0] or 0)
            discovered.append(
                {
                    "path": str(candidate),
                    "sales_rows": sales_rows,
                    "advertising_rows": advertising_rows,
                    "finance_rows": finance_rows,
                }
            )
            conn.close()
        except Exception:
            continue
    best = max(discovered, key=lambda item: (item["sales_rows"], item["advertising_rows"], item["finance_rows"]), default=None)
    return (Path(best["path"]) if best else None), discovered


def _sync_user_access_metadata(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    source_row = source_conn.execute(
        "SELECT telegram_id, username, tariff, is_active, role, subscription_until, created_at, updated_at "
        "FROM users WHERE telegram_id=?",
        (user_id,),
    ).fetchone()
    if not source_row:
        return {"status": "SOURCE_USER_MISSING"}
    target_conn.execute(
        """
        INSERT INTO users(telegram_id, username, tariff, is_active, role, subscription_until, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username=excluded.username,
            tariff=excluded.tariff,
            is_active=excluded.is_active,
            role=excluded.role,
            subscription_until=excluded.subscription_until,
            updated_at=excluded.updated_at
        """,
        (
            int(source_row["telegram_id"]),
            source_row["username"] or "unknown",
            source_row["tariff"] or "FREE",
            int(source_row["is_active"] or 1),
            source_row["role"] or "owner",
            source_row["subscription_until"],
            source_row["created_at"],
            source_row["updated_at"],
        ),
    )
    return {
        "status": "SYNCED",
        "telegram_id": int(source_row["telegram_id"]),
        "username": source_row["username"] or "unknown",
        "tariff": source_row["tariff"] or "FREE",
        "role": source_row["role"] or "owner",
        "subscription_until": source_row["subscription_until"],
    }


def _upsert_rows(
    source_conn: sqlite3.Connection,
    target_conn: sqlite3.Connection,
    table: str,
    select_sql: str,
    select_params: tuple[Any, ...],
    insert_columns: list[str],
    conflict_target: str,
    key_columns: list[str],
) -> dict[str, int]:
    source_rows = [dict(row) for row in source_conn.execute(select_sql, select_params).fetchall()]
    if not source_rows:
        return {"source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0}

    placeholders = ", ".join(["?"] * len(insert_columns))
    update_columns = [column for column in insert_columns if column not in key_columns]
    update_clause = ", ".join([f"{column}=excluded.{column}" for column in update_columns])
    insert_sql = (
        f"INSERT INTO {table}({', '.join(insert_columns)}) VALUES({placeholders}) "
        f"ON CONFLICT({conflict_target}) DO UPDATE SET {update_clause}"
    )

    stats = {"source_rows": len(source_rows), "inserted": 0, "updated": 0, "skipped": 0}
    for row in source_rows:
        key_values = [row[column] for column in key_columns]
        existing = target_conn.execute(
            f"SELECT {', '.join(insert_columns)} FROM {table} WHERE " + " AND ".join([f"{column}=?" for column in key_columns]),
            tuple(key_values),
        ).fetchone()
        values = [row[column] for column in insert_columns]
        if existing is None:
            target_conn.execute(insert_sql, tuple(values))
            stats["inserted"] += 1
            continue
        existing_values = [existing[column] for column in insert_columns]
        if list(existing_values) == values:
            stats["skipped"] += 1
            continue
        target_conn.execute(insert_sql, tuple(values))
        stats["updated"] += 1
    return stats


def _upsert_finance_raw(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, user_id: int, start_date: str, end_date: str) -> dict[str, int]:
    columns = [
        "telegram_id",
        "rrd_id",
        "report_date",
        "penalty",
        "deduction",
        "acceptance",
        "acceptance_fee",
        "additional_payment",
        "acquiring_fee",
        "nm_id",
        "supplier_article",
        "srid",
        "doc_type_name",
        "operation_type",
        "payment_type",
        "subject_name",
        "brand_name",
        "sa_name",
        "bonus_type_name",
        "sticker_id",
        "gi_id",
        "raw_json",
        "created_at",
    ]
    key_columns = [
        "telegram_id",
        "rrd_id",
        "report_date",
        "nm_id",
        "supplier_article",
        "srid",
        "doc_type_name",
        "operation_type",
        "payment_type",
        "sa_name",
        "bonus_type_name",
        "sticker_id",
        "gi_id",
    ]
    raw_source_rows = [
        dict(row)
        for row in source_conn.execute(
            f"SELECT {', '.join(columns)} FROM finance_raw_audit WHERE telegram_id=? AND substr(report_date,1,10) BETWEEN ? AND ?",
            (user_id, start_date, end_date),
        ).fetchall()
    ]
    if not raw_source_rows:
        return {"source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0}

    deduped_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in raw_source_rows:
        key = tuple(row[column] for column in key_columns)
        existing = deduped_rows.get(key)
        if existing is None:
            deduped_rows[key] = row
            continue
        # Prefer the most complete payload when the source contains duplicate logical rows.
        existing_score = sum(1 for value in existing.values() if value not in (None, "", 0, 0.0))
        row_score = sum(1 for value in row.values() if value not in (None, "", 0, 0.0))
        if row_score >= existing_score:
            deduped_rows[key] = row

    source_rows = list(deduped_rows.values())

    stats = {"source_rows": len(source_rows), "inserted": 0, "updated": 0, "skipped": 0}
    for row in source_rows:
        where_clause = " AND ".join([f"COALESCE({column},'')=COALESCE(?, '')" for column in key_columns])
        existing = target_conn.execute(
            f"SELECT rowid AS _rowid, {', '.join(columns)} FROM finance_raw_audit WHERE {where_clause}",
            tuple(row[column] for column in key_columns),
        ).fetchone()
        values = [row[column] for column in columns]
        if existing is None:
            target_conn.execute(
                f"INSERT INTO finance_raw_audit({', '.join(columns)}) VALUES({', '.join(['?'] * len(columns))})",
                tuple(values),
            )
            stats["inserted"] += 1
            continue
        existing_values = [existing[column] for column in columns]
        if existing_values == values:
            stats["skipped"] += 1
            continue
        target_conn.execute(
            "UPDATE finance_raw_audit SET "
            + ", ".join([f"{column}=?" for column in columns])
            + " WHERE rowid=?",
            tuple(values) + (existing["_rowid"],),
        )
        stats["updated"] += 1
    return stats


def _restore_from_caches(target_path: Path, user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
    original_db_name = load_sales.DB_NAME
    load_sales.DB_NAME = str(target_path)
    try:
        sales_result = load_sales.apply_historical_sales_backfill(user_id, "", start_date, end_date)
        ads_result = load_sales.apply_historical_advertising_backfill(user_id, "", start_date, end_date)
    finally:
        load_sales.DB_NAME = original_db_name
    return {"sales_cache": sales_result, "ads_cache": ads_result}


def _run_backfill(user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
    db_manager.init_db()
    target_path = Path(DB_NAME).resolve()
    source_path, discovered_sources = _discover_source_db(user_id, start_date, end_date)
    result: dict[str, Any] = {
        "target_db": str(target_path),
        "source_db": str(source_path) if source_path else None,
        "discovered_sources": discovered_sources,
        "tables": {},
        "user_access": {},
        "cache_fallbacks": {},
        "missing": [],
    }

    source_conn = _connect(source_path) if source_path else None
    target_conn = _connect(target_path)
    try:
        if source_conn is not None:
            result["user_access"] = _sync_user_access_metadata(source_conn, target_conn, user_id)

            plans: list[tuple[str, str | None, str, tuple[Any, ...], list[str], str, list[str]]] = [
                (
                    "sales",
                    "sale_date",
                    "SELECT sale_id, telegram_id, sale_date, supplier_article, nm_id, barcode, warehouse_name, category, brand, total_price, for_pay, finished_price, price_with_disc, is_return "
                    "FROM sales WHERE telegram_id=? AND substr(sale_date,1,10) BETWEEN ? AND ?",
                    (user_id, start_date, end_date),
                    ["sale_id", "telegram_id", "sale_date", "supplier_article", "nm_id", "barcode", "warehouse_name", "category", "brand", "total_price", "for_pay", "finished_price", "price_with_disc", "is_return"],
                    "sale_id",
                    ["sale_id"],
                ),
                (
                    "orders",
                    "order_date",
                    "SELECT order_id, telegram_id, order_date, supplier_article, nm_id, barcode, warehouse_name, category, brand, total_price, finished_price, price_with_disc, is_cancel, cancel_date "
                    "FROM orders WHERE telegram_id=? AND substr(order_date,1,10) BETWEEN ? AND ?",
                    (user_id, start_date, end_date),
                    ["order_id", "telegram_id", "order_date", "supplier_article", "nm_id", "barcode", "warehouse_name", "category", "brand", "total_price", "finished_price", "price_with_disc", "is_cancel", "cancel_date"],
                    "order_id",
                    ["order_id"],
                ),
                (
                    "advertising",
                    "advert_date",
                    "SELECT unique_key, telegram_id, advert_date, campaign_id, campaign_name, supplier_article, nm_id, app_type, name, views, clicks, orders, sum_price, spend, ctr, cpc, cr "
                    "FROM advertising WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?",
                    (user_id, start_date, end_date),
                    ["unique_key", "telegram_id", "advert_date", "campaign_id", "campaign_name", "supplier_article", "nm_id", "app_type", "name", "views", "clicks", "orders", "sum_price", "spend", "ctr", "cpc", "cr"],
                    "unique_key",
                    ["unique_key"],
                ),
                (
                    "expenses",
                    "expense_date",
                    "SELECT unique_key, telegram_id, expense_date, expense_type, amount, supplier_article, comment, source, created_at "
                    "FROM expenses WHERE telegram_id=? AND substr(expense_date,1,10) BETWEEN ? AND ?",
                    (user_id, start_date, end_date),
                    ["unique_key", "telegram_id", "expense_date", "expense_type", "amount", "supplier_article", "comment", "source", "created_at"],
                    "unique_key",
                    ["unique_key"],
                ),
                (
                    "products",
                    None,
                    "SELECT telegram_id, supplier_article, cost_price, last_price FROM products WHERE telegram_id IN (?,0)",
                    (user_id,),
                    ["telegram_id", "supplier_article", "cost_price", "last_price"],
                    "telegram_id, supplier_article",
                    ["telegram_id", "supplier_article"],
                ),
            ]

            for table, date_col, sql, params, columns, conflict_target, key_columns in plans:
                before = _table_summary(target_conn, table, date_col, user_id, start_date, end_date)
                stats = _upsert_rows(source_conn, target_conn, table, sql, params, columns, conflict_target, key_columns)
                after = _table_summary(target_conn, table, date_col, user_id, start_date, end_date)
                result["tables"][table] = {"before": before, "after": after, **stats}
                if stats["source_rows"] <= 0:
                    result["missing"].append(table)

            before_finance = _table_summary(target_conn, "finance_raw_audit", "report_date", user_id, start_date, end_date)
            finance_stats = _upsert_finance_raw(source_conn, target_conn, user_id, start_date, end_date)
            after_finance = _table_summary(target_conn, "finance_raw_audit", "report_date", user_id, start_date, end_date)
            result["tables"]["finance_raw_audit"] = {"before": before_finance, "after": after_finance, **finance_stats}
            if finance_stats["source_rows"] <= 0:
                result["missing"].append("finance_raw_audit")

            before_stocks = _table_summary(target_conn, "stocks", "stock_date", user_id, start_date, end_date)
            stocks_stats = _upsert_rows(
                source_conn,
                target_conn,
                "stocks",
                "SELECT unique_key, telegram_id, stock_date, supplier_article, nm_id, barcode, warehouse_name, quantity, quantity_full, in_way_to_client, in_way_from_client "
                "FROM stocks WHERE telegram_id=? AND substr(stock_date,1,10) BETWEEN ? AND ?",
                (user_id, start_date, end_date),
                ["unique_key", "telegram_id", "stock_date", "supplier_article", "nm_id", "barcode", "warehouse_name", "quantity", "quantity_full", "in_way_to_client", "in_way_from_client"],
                "unique_key",
                ["unique_key"],
            )
            after_stocks = _table_summary(target_conn, "stocks", "stock_date", user_id, start_date, end_date)
            result["tables"]["stocks"] = {"before": before_stocks, "after": after_stocks, **stocks_stats}

        target_conn.commit()
    finally:
        target_conn.close()
        if source_conn is not None:
            source_conn.close()

    cache_fallbacks = _restore_from_caches(target_path, user_id, start_date, end_date)
    result["cache_fallbacks"] = cache_fallbacks
    if result["tables"].get("sales", {}).get("after", {}).get("rows", 0) <= 0 and str((cache_fallbacks.get("sales_cache") or {}).get("status") or "") not in {"SUCCESS", "GUARD_BLOCKED"}:
        if "sales" not in result["missing"]:
            result["missing"].append("sales")
    if result["tables"].get("advertising", {}).get("after", {}).get("rows", 0) <= 0 and str((cache_fallbacks.get("ads_cache") or {}).get("status") or "") not in {"SUCCESS", "GUARD_BLOCKED"}:
        if "advertising" not in result["missing"]:
            result["missing"].append("advertising")

    return result


def _print_summary(result: dict[str, Any]) -> None:
    print(f"TARGET_DB {result.get('target_db')}")
    print(f"SOURCE_DB {result.get('source_db') or '-'}")
    print("DISCOVERED_SOURCES")
    for item in result.get("discovered_sources") or []:
        print(json.dumps(item, ensure_ascii=False))
    if result.get("user_access"):
        print("USER_ACCESS", json.dumps(result["user_access"], ensure_ascii=False))

    for table, payload in (result.get("tables") or {}).items():
        before = payload.get("before") or {}
        after = payload.get("after") or {}
        print(f"{table.upper()} before_rows={before.get('rows', 0)} after_rows={after.get('rows', 0)} inserted={payload.get('inserted', 0)} updated={payload.get('updated', 0)} skipped={payload.get('skipped', 0)} source_rows={payload.get('source_rows', 0)}")

    if result.get("cache_fallbacks"):
        print("CACHE_FALLBACKS")
        print(json.dumps(result["cache_fallbacks"], ensure_ascii=False))

    missing = sorted(set(result.get("missing") or []))
    if missing:
        print("MAY_SOURCE_DATA_MISSING")
        print("missing_tables=" + ",".join(missing))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Backfill financial source data for a historical period.")
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    result = _run_backfill(args.user_id, args.date_from, args.date_to)
    _print_summary(result)


if __name__ == "__main__":
    main()
