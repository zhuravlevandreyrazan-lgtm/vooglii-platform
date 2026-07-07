from __future__ import annotations

import json
import sqlite3

from config import DB_NAME
from db_manager import init_db
import load_sales
from vooglii_telegram import legacy_bot


def _expense_insert(cur, row: dict) -> None:
    if float(row.get("amount") or 0) <= 0:
        return
    cur.execute(
        """
        INSERT OR REPLACE INTO expenses (
            unique_key, telegram_id, expense_date, expense_type, amount,
            supplier_article, comment, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["unique_key"],
            row["telegram_id"],
            row["expense_date"],
            row["expense_type"],
            row["amount"],
            row["supplier_article"],
            row["comment"],
            row["source"],
            row["created_at"],
        ),
    )


def _persist_legacy_rows(user_id: int, raw_rows: list[dict], expense_rows: list[dict], date_from: str, date_to: str) -> dict:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            DELETE FROM expenses
            WHERE telegram_id=? AND source='api_finance' AND substr(expense_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(date_from), str(date_to)),
        )
        cur.execute(
            """
            DELETE FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(date_from), str(date_to)),
        )
        inserted_expenses = 0
        for row in expense_rows:
            _expense_insert(cur, row)
            if float(row.get("amount") or 0) > 0:
                inserted_expenses += 1
        cur.executemany(
            """
            INSERT INTO finance_raw_audit(
                telegram_id, rrd_id, report_date, penalty, deduction, acceptance,
                acceptance_fee, additional_payment, acquiring_fee, nm_id, supplier_article,
                srid, doc_type_name, operation_type, payment_type, subject_name, brand_name,
                sa_name, bonus_type_name, sticker_id, gi_id, raw_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["telegram_id"],
                    row["rrd_id"],
                    row["report_date"],
                    row["penalty"],
                    row["deduction"],
                    row["acceptance"],
                    row["acceptance_fee"],
                    row["additional_payment"],
                    row["acquiring_fee"],
                    row["nm_id"],
                    row["supplier_article"],
                    row["srid"],
                    row["doc_type_name"],
                    row["operation_type"],
                    row["payment_type"],
                    row["subject_name"],
                    row["brand_name"],
                    row["sa_name"],
                    row["bonus_type_name"],
                    row["sticker_id"],
                    row["gi_id"],
                    row["raw_json"],
                    row["created_at"],
                )
                for row in raw_rows
            ],
        )
        conn.commit()
        return {
            "inserted": inserted_expenses,
            "updated": 0,
            "skipped": 0,
            "invalid": 0,
            "source_rows": len(raw_rows),
        }
    finally:
        conn.close()


def _legacy_range_fetch(user_id: int, token: str, date_from: str, date_to: str) -> dict:
    rrdid = 0
    page = 0
    raw_rows: list[dict] = []
    expense_rows: list[dict] = []
    while True:
        page += 1
        data, status = load_sales._get(
            f"{load_sales.STAT_API}/api/v5/supplier/reportDetailByPeriod",
            token,
            {"dateFrom": date_from, "dateTo": date_to, "limit": 100000, "rrdid": rrdid},
            timeout=20,
            caller="vooglii_wb_sync.finance_loader->reportDetailByPeriod",
        )
        if status != "SUCCESS":
            return {"raw_status": status, "raw_rows": [], "expense_rows": [], "meta": {"fallback": "legacy"}}
        if not isinstance(data, list):
            return {"raw_status": "INVALID_RESPONSE", "raw_rows": [], "expense_rows": [], "meta": {"fallback": "legacy"}}
        if not data:
            break
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            d = str(load_sales._first(row, ["sale_dt", "rr_dt", "date", "operation_dt"], date_to))[:10]
            article = load_sales._first(row, ["sa_name", "supplierArticle", "supplier_article", "supplierArticleName"])
            nm_id = load_sales._first(row, ["nm_id", "nmID", "nmId"])
            supplier_article = load_sales._first(row, ["supplier_article", "supplierArticle", "sa_name", "saName"]) or article
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
                    "telegram_id": int(user_id),
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
                    "srid": None,
                    "doc_type_name": None,
                    "operation_type": None,
                    "payment_type": None,
                    "subject_name": None,
                    "brand_name": None,
                    "sa_name": None if article in (None, "") else str(article),
                    "bonus_type_name": None,
                    "sticker_id": None,
                    "gi_id": None,
                    "raw_json": json.dumps(row, ensure_ascii=False, default=str),
                    "created_at": load_sales._dt(),
                }
            )
            expense_rows.extend(
                [
                    {
                        "unique_key": f"finance:{user_id}:{row_rrd}:logistics",
                        "telegram_id": int(user_id),
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
                        "telegram_id": int(user_id),
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
                        "telegram_id": int(user_id),
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
        "raw_status": "SUCCESS",
        "raw_rows": raw_rows,
        "expense_rows": expense_rows,
        "meta": {"fallback": "legacy", "pages_loaded": page},
    }


def sync_finance(user_id: int, token: str, period: int | tuple[str, str]) -> dict:
    if isinstance(period, tuple):
        date_from, date_to = period
    else:
        date_from, date_to = load_sales._normalize_period_dates(period)

    primary = legacy_bot._finance_api_post(
        legacy_bot.FINANCE_REPORTS_DETAILED_PERIOD_ENDPOINT,
        token,
        body={"dateFrom": str(date_from), "dateTo": str(date_to)},
        timeout=25,
        caller="vooglii_wb_sync.finance_loader->sales-reports/detailed",
    )
    payload, status, diagnostics = primary
    normalized_rows = legacy_bot._finance_detail_extract_rows(payload) if status == "SUCCESS" else []
    if normalized_rows:
        stats = _legacy_range_fetch(user_id, token, date_from, date_to)
        persisted = _persist_legacy_rows(user_id, stats["raw_rows"], stats["expense_rows"], date_from, date_to)
        return {
            "raw_status": "SUCCESS",
            "source_name": "finance-api.sales-reports-detailed",
            "source_rows": int(len(normalized_rows)),
            "inserted": int(persisted.get("inserted") or 0),
            "updated": int(persisted.get("updated") or 0),
            "skipped": int(persisted.get("skipped") or 0),
            "invalid": int(persisted.get("invalid") or 0),
            "meta": {
                "primary_status": status,
                "primary_rows": len(normalized_rows),
                "fallback_persist": "legacy_report_detail_by_period",
                "diagnostics": diagnostics,
            },
        }
    fallback = _legacy_range_fetch(user_id, token, date_from, date_to)
    if fallback.get("raw_status") == "SUCCESS":
        persisted = _persist_legacy_rows(user_id, fallback["raw_rows"], fallback["expense_rows"], date_from, date_to)
        return {
            "raw_status": "SUCCESS",
            "source_name": "statistics-api.reportDetailByPeriod",
            "source_rows": int(persisted.get("source_rows") or 0),
            "inserted": int(persisted.get("inserted") or 0),
            "updated": int(persisted.get("updated") or 0),
            "skipped": int(persisted.get("skipped") or 0),
            "invalid": int(persisted.get("invalid") or 0),
            "meta": {
                "primary_status": status,
                "fallback": "legacy_report_detail_by_period",
                "diagnostics": diagnostics,
            },
        }
    return {
        "raw_status": fallback.get("raw_status") or status,
        "source_name": "finance-api.sales-reports-detailed",
        "source_rows": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "meta": {
            "primary_status": status,
            "fallback_status": fallback.get("raw_status"),
            "diagnostics": diagnostics,
        },
    }
