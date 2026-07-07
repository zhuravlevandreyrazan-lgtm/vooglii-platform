from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

import config
from db_manager import init_db


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _dt() -> str:
    import load_sales

    return load_sales._dt()


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def build_snapshot_key(user_id: int, period_start: str | None, period_end: str | None, snapshot: dict[str, Any]) -> str:
    payload = {
        "user_id": int(user_id or 0),
        "period_start": str(period_start or ""),
        "period_end": str(period_end or ""),
        "revenue": _money(snapshot.get("sales_revenue")),
        "expenses_total": _money(snapshot.get("expenses_total")),
        "net_profit": _money(snapshot.get("net_profit")),
        "finance_status": str(snapshot.get("finance_status") or ""),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def write_financial_snapshot_audit(user_id: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    period_start = str(snapshot.get("period_start") or "")
    period_end = str(snapshot.get("period_end") or "")
    period_key = f"{period_start}..{period_end}"
    snapshot_key = build_snapshot_key(user_id, period_start, period_end, snapshot)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO financial_snapshot_audit(
                user_id, period_start, period_end, period_key, snapshot_key,
                finance_status, finance_confidence, profit_display_mode,
                revenue, expenses_total, net_profit,
                source_map_json, warnings_json, snapshot_json, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(user_id),
                period_start,
                period_end,
                period_key,
                snapshot_key,
                str(snapshot.get("finance_status") or ""),
                str(snapshot.get("finance_confidence") or ""),
                str(snapshot.get("profit_display_mode") or ""),
                _money(snapshot.get("sales_revenue")),
                _money(snapshot.get("expenses_total")),
                _money(snapshot.get("net_profit")),
                json.dumps(snapshot.get("source_map") or {}, ensure_ascii=False, sort_keys=True),
                json.dumps(snapshot.get("warnings") or [], ensure_ascii=False),
                json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str),
                _dt(),
                _dt(),
            ),
        )
        conn.commit()
        return {"status": "OK", "snapshot_key": snapshot_key}
    finally:
        conn.close()


def _expense_category(expense_type: str) -> str:
    value = str(expense_type or "").strip().lower()
    if value in {"advertising", "logistics", "storage"}:
        return value
    if value in {"acquiring", "wb_deductions", "penalties", "acceptance", "returns", "compensation"}:
        return value
    if value in {"other", ""}:
        return "other"
    return "other"


def normalize_finance_expense_events(user_id: int, period_start: str, period_end: str) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        inserted = 0
        skipped = 0
        updated = 0

        cur.execute(
            """
            SELECT unique_key, advert_date, spend, nm_id, supplier_article
            FROM advertising
            WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ? AND COALESCE(spend,0) > 0
            """,
            (int(user_id), str(period_start), str(period_end)),
        )
        advertising_rows = cur.fetchall()
        has_advertising_source = bool(advertising_rows)
        for row in advertising_rows:
            event_id = f"advertising:{row['unique_key']}"
            before = conn.total_changes
            cur.execute(
                """
                INSERT OR REPLACE INTO finance_expense_events(
                    user_id, event_date, period_key, source_event_id, source_table, source_type,
                    expense_category, amount, currency, nm_id, supplier_article, finance_status,
                    raw_payload_json, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(user_id),
                    str(row["advert_date"])[:10],
                    f"{period_start}..{period_end}",
                    event_id,
                    "advertising",
                    "selected_source",
                    "advertising",
                    _number(row["spend"]),
                    "RUB",
                    None if row["nm_id"] in (None, "") else str(row["nm_id"]),
                    row["supplier_article"],
                    "CONFIRMED",
                    json.dumps(dict(row), ensure_ascii=False, default=str),
                    _dt(),
                    _dt(),
                ),
            )
            delta = conn.total_changes - before
            inserted += 1 if delta > 0 else 0
            skipped += 1 if delta == 0 else 0

        cur.execute(
            """
            SELECT unique_key, expense_date, expense_type, amount, supplier_article, source, comment
            FROM expenses
            WHERE telegram_id=? AND substr(expense_date,1,10) BETWEEN ? AND ? AND COALESCE(amount,0) > 0
            """,
            (int(user_id), str(period_start), str(period_end)),
        )
        for row in cur.fetchall():
            category = _expense_category(row["expense_type"])
            if category == "advertising" and has_advertising_source:
                skipped += 1
                continue
            event_id = f"expense:{row['unique_key']}"
            before = conn.total_changes
            cur.execute(
                """
                INSERT OR REPLACE INTO finance_expense_events(
                    user_id, event_date, period_key, source_event_id, source_table, source_type,
                    expense_category, amount, currency, supplier_article, finance_status,
                    raw_payload_json, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(user_id),
                    str(row["expense_date"])[:10],
                    f"{period_start}..{period_end}",
                    event_id,
                    "expenses",
                    str(row["source"] or "manual"),
                    category,
                    _number(row["amount"]),
                    "RUB",
                    row["supplier_article"],
                    "CONFIRMED" if str(row["source"] or "").startswith("api_") else "REFERENCE",
                    json.dumps(dict(row), ensure_ascii=False, default=str),
                    _dt(),
                    _dt(),
                ),
            )
            delta = conn.total_changes - before
            inserted += 1 if delta > 0 else 0
            skipped += 1 if delta == 0 else 0

        cur.execute(
            """
            SELECT id, report_date, deduction, acquiring_fee, penalty, acceptance, acceptance_fee, additional_payment, supplier_article, nm_id
            FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(period_start), str(period_end)),
        )
        for row in cur.fetchall():
            mapping = [
                ("wb_deductions", _number(abs(row["deduction"] or 0))),
                ("acquiring", _number(abs(row["acquiring_fee"] or 0))),
                ("penalties", _number(abs(row["penalty"] or 0))),
                ("other", _number(abs(row["acceptance"] or 0) + abs(row["acceptance_fee"] or 0) + abs(row["additional_payment"] or 0))),
            ]
            for category, amount in mapping:
                if amount <= 0:
                    continue
                event_id = f"finance_raw:{row['id']}:{category}"
                before = conn.total_changes
                cur.execute(
                    """
                    INSERT OR REPLACE INTO finance_expense_events(
                        user_id, event_date, period_key, source_event_id, source_table, source_type,
                        expense_category, amount, currency, nm_id, supplier_article, finance_status,
                        raw_payload_json, created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        int(user_id),
                        str(row["report_date"])[:10],
                        f"{period_start}..{period_end}",
                        event_id,
                        "finance_raw_audit",
                        "wb_finance",
                        category,
                        amount,
                        "RUB",
                        None if row["nm_id"] in (None, "") else str(row["nm_id"]),
                        row["supplier_article"],
                        "PENDING",
                        json.dumps(dict(row), ensure_ascii=False, default=str),
                        _dt(),
                        _dt(),
                    ),
                )
                delta = conn.total_changes - before
                inserted += 1 if delta > 0 else 0
                updated += 1 if delta > 0 else 0

        conn.commit()
        return {"status": "OK", "inserted": inserted, "updated": updated, "skipped": skipped}
    finally:
        conn.close()


def get_normalized_expense_summary(user_id: int, period_start: str, period_end: str, *, autoload: bool = True) -> dict[str, Any]:
    if autoload:
        try:
            normalize_finance_expense_events(user_id, period_start, period_end)
        except Exception:
            pass
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT expense_category, COUNT(*) AS rows_count, ROUND(COALESCE(SUM(amount),0),2) AS total_amount,
                   MIN(event_date) AS min_date, MAX(event_date) AS max_date
            FROM finance_expense_events
            WHERE user_id=? AND substr(event_date,1,10) BETWEEN ? AND ?
            GROUP BY expense_category
            ORDER BY expense_category
            """,
            (int(user_id), str(period_start), str(period_end)),
        )
        categories: dict[str, Any] = {}
        total_rows = 0
        for row in cur.fetchall():
            categories[str(row["expense_category"] or "")] = {
                "rows": int(row["rows_count"] or 0),
                "amount": _money(row["total_amount"]),
                "min_date": row["min_date"],
                "max_date": row["max_date"],
                "source_table": "finance_expense_events",
                "fallback": False,
            }
            total_rows += int(row["rows_count"] or 0)
        return {"rows_total": total_rows, "categories": categories}
    finally:
        conn.close()


def write_stock_snapshots_from_stocks(user_id: int, snapshot_date: str | None = None) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        if snapshot_date:
            cur.execute(
                """
                SELECT unique_key, stock_date, supplier_article, nm_id, barcode, warehouse_name,
                       quantity, quantity_full, in_way_to_client, in_way_from_client
                FROM stocks
                WHERE telegram_id=? AND substr(stock_date,1,10)=?
                """,
                (int(user_id), str(snapshot_date)),
            )
        else:
            cur.execute(
                """
                SELECT unique_key, stock_date, supplier_article, nm_id, barcode, warehouse_name,
                       quantity, quantity_full, in_way_to_client, in_way_from_client
                FROM stocks
                WHERE telegram_id=?
                """,
                (int(user_id),),
            )
        rows = cur.fetchall()
        inserted = 0
        for row in rows:
            snapshot_id = f"stocks:{row['unique_key']}"
            before = conn.total_changes
            cur.execute(
                """
                INSERT OR REPLACE INTO stock_snapshots(
                    user_id, snapshot_date, period_key, source_snapshot_id, source_type,
                    supplier_article, nm_id, barcode, warehouse_name,
                    quantity, quantity_full, in_way_to_client, in_way_from_client,
                    is_historical_available, raw_payload_json, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    int(user_id),
                    str(row["stock_date"])[:10],
                    str(row["stock_date"])[:10],
                    snapshot_id,
                    "stocks_table_bridge",
                    row["supplier_article"],
                    None if row["nm_id"] in (None, "") else str(row["nm_id"]),
                    row["barcode"],
                    row["warehouse_name"],
                    int(row["quantity"] or 0),
                    int(row["quantity_full"] or 0),
                    int(row["in_way_to_client"] or 0),
                    int(row["in_way_from_client"] or 0),
                    1,
                    json.dumps(dict(row), ensure_ascii=False, default=str),
                    _dt(),
                    _dt(),
                ),
            )
            delta = conn.total_changes - before
            inserted += 1 if delta > 0 else 0
        conn.commit()
        return {"status": "OK", "rows": len(rows), "inserted": inserted}
    finally:
        conn.close()


def get_latest_stock_snapshot_info(user_id: int) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT snapshot_date, COUNT(*) AS rows_count
            FROM stock_snapshots
            WHERE user_id=?
            GROUP BY snapshot_date
            ORDER BY snapshot_date DESC
            LIMIT 1
            """,
            (int(user_id),),
        ).fetchone()
        if not row:
            return {"snapshot_date": None, "rows": 0}
        return {"snapshot_date": row["snapshot_date"], "rows": int(row["rows_count"] or 0)}
    finally:
        conn.close()


def get_snapshot_audit_rows(user_id: int, period_start: str, period_end: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT snapshot_key, finance_status, finance_confidence, profit_display_mode,
                   revenue, expenses_total, net_profit, source_map_json, warnings_json, created_at, updated_at
            FROM financial_snapshot_audit
            WHERE user_id=? AND period_start=? AND period_end=?
            ORDER BY updated_at DESC, id DESC
            """,
            (int(user_id), str(period_start), str(period_end)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
