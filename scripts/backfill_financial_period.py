from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME, WB_TOKEN
import db_manager
import load_sales
import telegram_bot
from user_manager import get_user
from vooglii_telegram.services.token_resolver import resolve_wb_token
from vooglii_wb_sync.sync_orchestrator import run_backfill_sync


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


def _upsert_rows_from_payload(
    target_conn: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    insert_columns: list[str],
    key_columns: list[str],
) -> dict[str, int]:
    if not rows:
        return {"source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0}
    placeholders = ", ".join(["?"] * len(insert_columns))
    update_columns = [column for column in insert_columns if column not in key_columns]
    update_clause = ", ".join([f"{column}=excluded.{column}" for column in update_columns])
    insert_sql = (
        f"INSERT INTO {table}({', '.join(insert_columns)}) VALUES({placeholders}) "
        f"ON CONFLICT({', '.join(key_columns)}) DO UPDATE SET {update_clause}"
    )
    stats = {"source_rows": len(rows), "inserted": 0, "updated": 0, "skipped": 0}
    for row in rows:
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


def _upsert_finance_raw_rows(target_conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> dict[str, int]:
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
    if not rows:
        return {"source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0}
    stats = {"source_rows": len(rows), "inserted": 0, "updated": 0, "skipped": 0}
    for row in rows:
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
            "UPDATE finance_raw_audit SET " + ", ".join([f"{column}=?" for column in columns]) + " WHERE rowid=?",
            tuple(values) + (existing["_rowid"],),
        )
        stats["updated"] += 1
    return stats


def _fetch_finance_api_range(user_id: int, token: str, start_date: str, end_date: str) -> dict[str, Any]:
    rrdid = 0
    page = 0
    raw_rows: list[dict[str, Any]] = []
    expenses_rows: list[dict[str, Any]] = []
    while True:
        page += 1
        data, status = load_sales._get(
            f"{load_sales.STAT_API}/api/v5/supplier/reportDetailByPeriod",
            token,
            {"dateFrom": start_date, "dateTo": end_date, "limit": 100000, "rrdid": rrdid},
            timeout=20,
            caller="scripts.backfill_financial_period->reportDetailByPeriod",
        )
        if status != "SUCCESS":
            return {
                "status": f"WB_API_UNAVAILABLE_FOR_PERIOD:{status}",
                "pages_loaded": page,
                "raw_rows": [],
                "expense_rows": [],
            }
        if not isinstance(data, list):
            return {
                "status": "WB_API_UNAVAILABLE_FOR_PERIOD:INVALID_RESPONSE",
                "pages_loaded": page,
                "raw_rows": [],
                "expense_rows": [],
            }
        if not data:
            break
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            d = str(load_sales._first(row, ["sale_dt", "rr_dt", "date", "operation_dt"], end_date))[:10]
            article = load_sales._first(row, ["sa_name", "supplierArticle", "supplier_article", "supplierArticleName"])
            nm_id = load_sales._first(row, ["nm_id", "nmID", "nmId"])
            supplier_article = load_sales._first(row, ["supplier_article", "supplierArticle", "sa_name", "saName"]) or article
            srid = load_sales._first(row, ["srid", "srId"])
            doc_type_name = load_sales._first(row, ["doc_type_name", "docTypeName", "doc_type"])
            operation_type = load_sales._first(row, ["operation_type", "operationType"])
            payment_type = load_sales._first(row, ["payment_type", "paymentType"])
            subject_name = load_sales._first(row, ["subject_name", "subjectName"])
            brand_name = load_sales._first(row, ["brand_name", "brandName"])
            sa_name = load_sales._first(row, ["sa_name", "saName"])
            bonus_type_name = load_sales._first(row, ["bonus_type_name", "bonusTypeName"])
            sticker_id = load_sales._first(row, ["sticker_id", "stickerId"])
            gi_id = load_sales._first(row, ["gi_id", "giId"])
            row_rrd = load_sales._first(row, ["rrd_id", "rrdId", "rrdid"], f"{page}:{idx}")
            penalty = load_sales._num(row.get("penalty"))
            deduction = load_sales._num(row.get("deduction"))
            acceptance = load_sales._num(row.get("acceptance"))
            acceptance_fee = load_sales._num(row.get("acceptance_fee")) + load_sales._num(row.get("acceptanceFee"))
            additional_payment = load_sales._num(row.get("additional_payment")) + load_sales._num(row.get("additionalPayment"))
            acquiring_fee = load_sales._num(row.get("acquiring_fee")) + load_sales._num(row.get("acquiringFee"))
            logistics = sum(abs(load_sales._num(row.get(x))) for x in [
                "delivery_rub", "deliveryRub", "return_amount", "returnAmount",
                "rebill_logistic_cost", "rebillLogisticCost", "delivery_amount", "deliveryAmount",
            ])
            storage = sum(abs(load_sales._num(row.get(x))) for x in [
                "storage_fee", "storageFee", "storage", "storage_cost", "storageCost",
            ])
            other = sum(abs(v) for v in [penalty, deduction, acceptance, acceptance_fee, additional_payment, acquiring_fee])
            raw_rows.append(
                {
                    "telegram_id": user_id,
                    "rrd_id": str(row_rrd),
                    "report_date": d,
                    "penalty": float(penalty),
                    "deduction": float(deduction),
                    "acceptance": float(acceptance),
                    "acceptance_fee": float(acceptance_fee),
                    "additional_payment": float(additional_payment),
                    "acquiring_fee": float(acquiring_fee),
                    "nm_id": None if nm_id in (None, "") else str(nm_id),
                    "supplier_article": None if supplier_article in (None, "") else str(supplier_article),
                    "srid": None if srid in (None, "") else str(srid),
                    "doc_type_name": None if doc_type_name in (None, "") else str(doc_type_name),
                    "operation_type": None if operation_type in (None, "") else str(operation_type),
                    "payment_type": None if payment_type in (None, "") else str(payment_type),
                    "subject_name": None if subject_name in (None, "") else str(subject_name),
                    "brand_name": None if brand_name in (None, "") else str(brand_name),
                    "sa_name": None if sa_name in (None, "") else str(sa_name),
                    "bonus_type_name": None if bonus_type_name in (None, "") else str(bonus_type_name),
                    "sticker_id": None if sticker_id in (None, "") else str(sticker_id),
                    "gi_id": None if gi_id in (None, "") else str(gi_id),
                    "raw_json": json.dumps(row, ensure_ascii=False, default=str),
                    "created_at": load_sales._dt(),
                }
            )
            expenses_rows.extend(
                [
                    {
                        "unique_key": f"finance:{user_id}:{row_rrd}:logistics",
                        "telegram_id": user_id,
                        "expense_date": d,
                        "expense_type": "logistics",
                        "amount": float(logistics),
                        "supplier_article": article,
                        "comment": "WB finance logistics",
                        "source": "api_finance",
                        "created_at": load_sales._dt(),
                    },
                    {
                        "unique_key": f"finance:{user_id}:{row_rrd}:storage",
                        "telegram_id": user_id,
                        "expense_date": d,
                        "expense_type": "storage",
                        "amount": float(storage),
                        "supplier_article": article,
                        "comment": "WB finance storage",
                        "source": "api_finance",
                        "created_at": load_sales._dt(),
                    },
                    {
                        "unique_key": f"finance:{user_id}:{row_rrd}:other",
                        "telegram_id": user_id,
                        "expense_date": d,
                        "expense_type": "other",
                        "amount": float(other),
                        "supplier_article": article,
                        "comment": "WB finance other",
                        "source": "api_finance",
                        "created_at": load_sales._dt(),
                    },
                ]
            )
            next_rrd = load_sales._first(row, ["rrd_id", "rrdId", "rrdid"])
            if next_rrd:
                try:
                    rrdid = int(next_rrd)
                except Exception:
                    pass
        if len(data) < 100000 or page >= 10:
            break
    return {
        "status": "SUCCESS",
        "pages_loaded": page,
        "raw_rows": raw_rows,
        "expense_rows": expenses_rows,
    }


def _run_diagnose(user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "diagnose_financial_period.py"),
        "--user-id",
        str(user_id),
        "--from",
        str(start_date),
        "--to",
        str(end_date),
    ]
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8")
    return {
        "status": "SUCCESS" if completed.returncode == 0 else f"FAILED:{completed.returncode}",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _resolve_wb_api_token(user_id: int) -> tuple[str | None, str]:
    resolution = resolve_wb_token(user_id)
    return resolution.token, resolution.source if resolution.token else "missing"


def _run_backfill_from_db(user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
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


def _run_backfill_from_wb_api(user_id: int, start_date: str, end_date: str) -> dict[str, Any]:
    db_manager.init_db()
    resolution = resolve_wb_token(user_id)
    token, token_source = resolution.token, resolution.source
    user_row = get_user(user_id)
    target_path = Path(DB_NAME).resolve()
    result: dict[str, Any] = {
        "target_db": str(target_path),
        "source_db": "wb-api",
        "discovered_sources": [],
        "tables": {},
        "user_access": {
            "telegram_id": int(user_row[0] or user_id) if user_row else user_id,
            "username": user_row[1] if user_row else None,
            "tariff": user_row[3] if user_row else None,
            "role": user_row[7] if user_row else None,
            "subscription_until": user_row[8] if user_row else None,
        },
        "api_blocks": {},
        "cache_fallbacks": {},
        "missing": [],
    }
    if not token:
        result["api_blocks"]["token"] = {
            "status": "WB_API_UNAVAILABLE_FOR_PERIOD:NO_TOKEN",
            "token_source": resolution.source,
            "token_len": resolution.token_len,
            "encrypted": resolution.encrypted,
            "reason": resolution.reason,
        }
        result["missing"] = ["sales", "orders", "advertising", "finance_raw_audit", "expenses", "stocks"]
        return result
    result["api_blocks"]["token"] = {
        "status": "SUCCESS",
        "token_source": token_source,
        "token_len": resolution.token_len,
        "encrypted": resolution.encrypted,
    }

    target_conn = _connect(target_path)
    try:
        before_map = {
            "sales": _table_summary(target_conn, "sales", "sale_date", user_id, start_date, end_date),
            "orders": _table_summary(target_conn, "orders", "order_date", user_id, start_date, end_date),
            "products": _table_summary(target_conn, "products", None, user_id, start_date, end_date),
            "advertising": _table_summary(target_conn, "advertising", "advert_date", user_id, start_date, end_date),
            "expenses": _table_summary(target_conn, "expenses", "expense_date", user_id, start_date, end_date),
            "finance_raw_audit": _table_summary(target_conn, "finance_raw_audit", "report_date", user_id, start_date, end_date),
            "stocks": _table_summary(target_conn, "stocks", "stock_date", user_id, start_date, end_date),
        }
        sync_result = run_backfill_sync(user_id, start_date, end_date, token=token)
        block_map = sync_result.get("blocks") or {}
        after_map = {
            "sales": _table_summary(target_conn, "sales", "sale_date", user_id, start_date, end_date),
            "orders": _table_summary(target_conn, "orders", "order_date", user_id, start_date, end_date),
            "products": _table_summary(target_conn, "products", None, user_id, start_date, end_date),
            "advertising": _table_summary(target_conn, "advertising", "advert_date", user_id, start_date, end_date),
            "expenses": _table_summary(target_conn, "expenses", "expense_date", user_id, start_date, end_date),
            "finance_raw_audit": _table_summary(target_conn, "finance_raw_audit", "report_date", user_id, start_date, end_date),
            "stocks": _table_summary(target_conn, "stocks", "stock_date", user_id, start_date, end_date),
        }
        table_block_map = {
            "sales": "sales",
            "orders": "orders",
            "products": "products",
            "advertising": "advertising",
            "expenses": "finance",
            "finance_raw_audit": "finance",
            "stocks": "stocks",
        }
        for table_name, block_name in table_block_map.items():
            block = block_map.get(block_name) or {}
            result["tables"][table_name] = {
                "before": before_map[table_name],
                "after": after_map[table_name],
                "inserted": int(block.get("rows_inserted") or 0),
                "updated": int(block.get("rows_updated") or 0),
                "skipped": int(block.get("rows_skipped") or 0),
                "source_rows": int(block.get("source_rows") or 0),
                "status": block.get("raw_status") or block.get("status"),
            }
            if int(block.get("source_rows") or 0) <= 0 and table_name != "products":
                result["missing"].append(table_name)
        for block_name in ("sales", "orders", "finance", "advertising", "stocks", "products"):
            block = block_map.get(block_name) or {}
            result["api_blocks"][block_name] = {
                "status": block.get("raw_status") or block.get("status") or "WB_API_UNAVAILABLE_FOR_PERIOD",
                "sync_status": block.get("status"),
                "rows_in_range": int(block.get("source_rows") or 0),
                "next_allowed_at": block.get("next_allowed_at"),
            }
    finally:
        target_conn.close()

    result["diagnose"] = _run_diagnose(user_id, start_date, end_date)
    return result


def _run_backfill(user_id: int, start_date: str, end_date: str, source: str) -> dict[str, Any]:
    source_key = str(source or "source-db").strip().lower()
    if source_key == "wb-api":
        return _run_backfill_from_wb_api(user_id, start_date, end_date)
    return _run_backfill_from_db(user_id, start_date, end_date)


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
    if result.get("api_blocks"):
        print("API_BLOCKS")
        print(json.dumps(result["api_blocks"], ensure_ascii=False))
    if result.get("diagnose"):
        print("DIAGNOSE_STATUS", result["diagnose"].get("status"))
        stdout = str(result["diagnose"].get("stdout") or "").strip()
        if stdout:
            print("DIAGNOSE_OUTPUT_BEGIN")
            print(stdout)
            print("DIAGNOSE_OUTPUT_END")

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
    parser.add_argument("--source", default="source-db", choices=["source-db", "wb-api"])
    args = parser.parse_args()

    result = _run_backfill(args.user_id, args.date_from, args.date_to, args.source)
    _print_summary(result)


if __name__ == "__main__":
    main()
