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


def _source_hash(payload: Any) -> str:
    raw = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _event_confidence(source_table: str, source_type: str, expense_category: str, finance_status: str) -> str:
    source_table = str(source_table or "").strip().lower()
    source_type = str(source_type or "").strip().lower()
    expense_category = str(expense_category or "").strip().lower()
    finance_status = str(finance_status or "").strip().upper()
    if source_table == "finance_raw_audit" and finance_status in {"CONFIRMED", "PENDING"}:
        return "HIGH"
    if source_table == "advertising" and expense_category == "advertising":
        return "HIGH"
    if source_table == "expenses" and source_type.startswith("api_") and expense_category in {"logistics", "storage"}:
        return "MEDIUM"
    if source_table == "expenses" and source_type.startswith("api_"):
        return "LOW"
    if source_type in {"manual", "manual_reference"}:
        return "LOW"
    return "UNKNOWN"


def _is_traceable_expense_event(source_table: str, source_type: str) -> bool:
    source_table = str(source_table or "").strip().lower()
    source_type = str(source_type or "").strip().lower()
    if source_table in {"finance_raw_audit", "advertising"}:
        return True
    return source_table == "expenses" and source_type.startswith("api_")


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
            source_type = str(row["source"] or "manual").strip() or "manual"
            finance_status = "CONFIRMED" if source_type.startswith("api_") else "REFERENCE"
            if category == "other":
                finance_status = "PENDING" if source_type.startswith("api_") else "REFERENCE"
            if not source_type.startswith("api_") and source_type == "manual":
                source_type = "manual_reference"
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
                    source_type,
                    category,
                    _number(row["amount"]),
                    "RUB",
                    row["supplier_article"],
                    finance_status,
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
            SELECT expense_category,
                   COUNT(*) AS rows_count,
                   ROUND(COALESCE(SUM(amount),0),2) AS total_amount,
                   MIN(event_date) AS min_date,
                   MAX(event_date) AS max_date,
                   COUNT(DISTINCT source_event_id) AS unique_documents,
                   COUNT(DISTINCT source_table) AS unique_sources,
                   GROUP_CONCAT(DISTINCT COALESCE(source_table,'')) AS source_tables,
                   GROUP_CONCAT(DISTINCT COALESCE(source_type,'')) AS source_types,
                   GROUP_CONCAT(DISTINCT COALESCE(finance_status,'')) AS finance_statuses
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
                "unique_documents": int(row["unique_documents"] or 0),
                "unique_sources": int(row["unique_sources"] or 0),
                "source_tables": [item for item in str(row["source_tables"] or "").split(",") if item],
                "source_types": [item for item in str(row["source_types"] or "").split(",") if item],
                "finance_statuses": [item for item in str(row["finance_statuses"] or "").split(",") if item],
                "traceable": all(
                    _is_traceable_expense_event(source_table, source_type)
                    for source_table in [item for item in str(row["source_tables"] or "").split(",") if item]
                    for source_type in [item for item in str(row["source_types"] or "").split(",") if item]
                ) if str(row["source_tables"] or "").strip() else False,
                "fallback": False,
            }
            total_rows += int(row["rows_count"] or 0)
        return {"rows_total": total_rows, "categories": categories}
    finally:
        conn.close()


def get_finance_expense_event_category_audit(user_id: int, period_start: str, period_end: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
                expense_category,
                source_table,
                source_type,
                finance_status,
                COUNT(*) AS rows_count,
                COUNT(DISTINCT source_event_id) AS unique_source_ids,
                MIN(event_date) AS min_date,
                MAX(event_date) AS max_date,
                ROUND(COALESCE(SUM(amount),0),2) AS total_amount
            FROM finance_expense_events
            WHERE user_id=? AND substr(event_date,1,10) BETWEEN ? AND ?
            GROUP BY expense_category, source_table, source_type, finance_status
            ORDER BY expense_category ASC, source_table ASC, source_type ASC, finance_status ASC
            """,
            (int(user_id), str(period_start), str(period_end)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_finance_expense_event_trace(user_id: int, period_start: str, period_end: str, category: str, *, limit: int = 100) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
                source_event_id,
                amount,
                event_date,
                source_type,
                source_table,
                finance_status,
                supplier_article,
                nm_id,
                created_at,
                raw_payload_json
            FROM finance_expense_events
            WHERE user_id=?
              AND expense_category=?
              AND substr(event_date,1,10) BETWEEN ? AND ?
            ORDER BY event_date ASC, amount DESC, source_event_id ASC
            LIMIT ?
            """,
            (int(user_id), str(category), str(period_start), str(period_end), int(limit)),
        ).fetchall()
        payload = []
        for row in rows:
            item = dict(row)
            raw_payload = item.pop("raw_payload_json", None)
            try:
                source_payload = json.loads(raw_payload) if raw_payload else {}
            except Exception:
                source_payload = {"raw_payload": raw_payload}
            item["source_id"] = item.get("source_event_id")
            item["event_id"] = item.get("source_event_id")
            item["source_hash"] = _source_hash(source_payload)
            item["confidence"] = _event_confidence(
                item.get("source_table"),
                item.get("source_type"),
                category,
                item.get("finance_status"),
            )
            item["status"] = item.get("finance_status")
            item["traceable"] = _is_traceable_expense_event(item.get("source_table"), item.get("source_type"))
            item["raw_source"] = source_payload
            payload.append(item)
        return payload
    finally:
        conn.close()


def get_finance_expense_event_duplicates(user_id: int, period_start: str, period_end: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
                expense_category,
                source_table,
                source_event_id,
                event_date,
                nm_id,
                supplier_article,
                ROUND(amount, 2) AS amount,
                COUNT(*) AS duplicate_rows
            FROM finance_expense_events
            WHERE user_id=? AND substr(event_date,1,10) BETWEEN ? AND ?
            GROUP BY expense_category, source_table, source_event_id, event_date, nm_id, supplier_article, ROUND(amount, 2)
            HAVING COUNT(*) > 1
            ORDER BY duplicate_rows DESC, expense_category ASC, source_event_id ASC
            """,
            (int(user_id), str(period_start), str(period_end)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_finance_expense_event_out_of_period_rows(user_id: int, period_start: str, period_end: str, *, limit: int = 100) -> list[dict[str, Any]]:
    period_key = f"{period_start}..{period_end}"
    conn = _connect()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
                expense_category,
                source_table,
                source_event_id,
                event_date,
                period_key,
                amount,
                nm_id,
                supplier_article
            FROM finance_expense_events
            WHERE user_id=?
              AND period_key=?
              AND (
                    substr(event_date,1,10) < ?
                 OR substr(event_date,1,10) > ?
              )
            ORDER BY event_date ASC, expense_category ASC, source_event_id ASC
            LIMIT ?
            """,
            (int(user_id), period_key, str(period_start), str(period_end), int(limit)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_finance_raw_category_summary(user_id: int, period_start: str, period_end: str) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT
                COUNT(*) AS rows_count,
                MIN(substr(report_date,1,10)) AS min_date,
                MAX(substr(report_date,1,10)) AS max_date,
                ROUND(COALESCE(SUM(ABS(COALESCE(deduction,0))),0),2) AS wb_deductions,
                ROUND(COALESCE(SUM(ABS(COALESCE(acquiring_fee,0))),0),2) AS acquiring,
                ROUND(COALESCE(SUM(ABS(COALESCE(penalty,0))),0),2) AS penalties,
                ROUND(COALESCE(SUM(ABS(COALESCE(acceptance,0)) + ABS(COALESCE(acceptance_fee,0)) + ABS(COALESCE(additional_payment,0))),0),2) AS other
            FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(period_start), str(period_end)),
        ).fetchone()
        payload = dict(row or {})
        payload.setdefault("rows_count", 0)
        return payload
    finally:
        conn.close()


def get_advertising_source_summary(user_id: int, period_start: str, period_end: str) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT
                COUNT(*) AS rows_count,
                MIN(substr(advert_date,1,10)) AS min_date,
                MAX(substr(advert_date,1,10)) AS max_date,
                ROUND(COALESCE(SUM(spend),0),2) AS total_amount
            FROM advertising
            WHERE telegram_id=? AND substr(advert_date,1,10) BETWEEN ? AND ?
            """,
            (int(user_id), str(period_start), str(period_end)),
        ).fetchone()
        return dict(row or {})
    finally:
        conn.close()


def build_finance_source_integrity_report(user_id: int, period_start: str, period_end: str, *, autoload: bool = True) -> dict[str, Any]:
    if autoload:
        normalize_finance_expense_events(user_id, period_start, period_end)
    expense_summary = get_normalized_expense_summary(user_id, period_start, period_end, autoload=False)
    category_audit = get_finance_expense_event_category_audit(user_id, period_start, period_end)
    duplicates = get_finance_expense_event_duplicates(user_id, period_start, period_end)
    out_of_period = get_finance_expense_event_out_of_period_rows(user_id, period_start, period_end)
    finance_raw = get_finance_raw_category_summary(user_id, period_start, period_end)
    advertising_source = get_advertising_source_summary(user_id, period_start, period_end)
    categories = dict(expense_summary.get("categories") or {})

    finance_raw_to_events = {
        "wb_deductions": {
            "finance_raw_audit": _money(finance_raw.get("wb_deductions")),
            "finance_expense_events": _money(((categories.get("wb_deductions") or {}).get("amount"))),
        },
        "acquiring": {
            "finance_raw_audit": _money(finance_raw.get("acquiring")),
            "finance_expense_events": _money(((categories.get("acquiring") or {}).get("amount"))),
        },
        "penalties": {
            "finance_raw_audit": _money(finance_raw.get("penalties")),
            "finance_expense_events": _money(((categories.get("penalties") or {}).get("amount"))),
        },
        "other": {
            "finance_raw_audit": _money(finance_raw.get("other")),
            "finance_expense_events": _money(((categories.get("other") or {}).get("amount"))),
        },
    }
    mismatches: list[dict[str, Any]] = []
    accepted_warnings: list[dict[str, Any]] = []
    for category, values in finance_raw_to_events.items():
        if abs(float(values["finance_raw_audit"] or 0) - float(values["finance_expense_events"] or 0)) > 0.01:
            mismatch = {
                "category": category,
                "finance_raw_audit": values["finance_raw_audit"],
                "finance_expense_events": values["finance_expense_events"],
            }
            if category == "other":
                other_category = dict(categories.get("other") or {})
                source_tables = set(other_category.get("source_tables") or [])
                source_types = set(other_category.get("source_types") or [])
                if source_tables == {"expenses"} and source_types == {"api_finance"} and bool(other_category.get("traceable")):
                    accepted_warnings.append({
                        **mismatch,
                        "reason": "other expenses are traceable to legacy expenses/api_finance rows, not finance_raw_audit",
                    })
                    continue
            mismatches.append(mismatch)

    advertising_drift = round(
        abs(float(advertising_source.get("total_amount") or 0) - float(((categories.get("advertising") or {}).get("amount")) or 0)),
        2,
    )
    if advertising_drift > 0:
        drift_payload = {
            "category": "advertising",
            "advertising_table": _money(advertising_source.get("total_amount")),
            "finance_expense_events": _money(((categories.get("advertising") or {}).get("amount"))),
            "drift": advertising_drift,
        }
        if advertising_drift < 1.0:
            accepted_warnings.append({
                **drift_payload,
                "reason": "customer advertising source is stable; minor aggregation drift stays in source_map",
            })
        else:
            mismatches.append({
                **drift_payload,
                "finance_raw_audit": None,
            })

    hard_failures = bool(duplicates or out_of_period or mismatches)
    return {
        "status": "PASS" if not hard_failures else "FAIL",
        "period_start": str(period_start),
        "period_end": str(period_end),
        "rows_total": int(expense_summary.get("rows_total") or 0),
        "categories": categories,
        "category_audit": category_audit,
        "finance_raw_summary": finance_raw,
        "advertising_source_summary": advertising_source,
        "finance_raw_to_events": finance_raw_to_events,
        "duplicates": duplicates,
        "out_of_period_rows": out_of_period,
        "mismatches": mismatches,
        "accepted_warnings": accepted_warnings,
    }


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
