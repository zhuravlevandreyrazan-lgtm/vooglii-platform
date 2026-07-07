from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME
from db_manager import init_db


REQUIRED_TABLES = {
    "sales": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("sale_date",), "unique_columns": ("sale_id",)},
    "orders": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("order_date",), "unique_columns": ("order_id",)},
    "advertising": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("advert_date",), "unique_columns": ("unique_key",)},
    "expenses": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("expense_date",), "unique_columns": ("unique_key",)},
    "finance_raw_audit": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("report_date",), "unique_columns": ("id", "rrd_id")},
    "stocks": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("stock_date",), "unique_columns": ("unique_key",)},
    "sync_state": {"user_columns": ("telegram_id", "user_id"), "date_columns": ("updated_at",), "unique_columns": ("sync_block",)},
    "finance_expense_events": {"user_columns": ("user_id",), "date_columns": ("event_date",), "unique_columns": ("source_event_id",)},
    "stock_snapshots": {"user_columns": ("user_id",), "date_columns": ("snapshot_date",), "unique_columns": ("source_snapshot_id",)},
    "financial_snapshot_audit": {"user_columns": ("user_id",), "date_columns": ("period_start", "period_end"), "unique_columns": ("snapshot_key",)},
}


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _table_names(cur: sqlite3.Cursor) -> list[str]:
    return [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]


def _index_names(cur: sqlite3.Cursor) -> list[str]:
    return [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]


def _table_columns(cur: sqlite3.Cursor, table: str) -> list[dict[str, Any]]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [
        {
            "cid": int(row[0]),
            "name": str(row[1]),
            "type": str(row[2] or ""),
            "notnull": bool(row[3]),
            "default": row[4],
            "pk": int(row[5] or 0),
        }
        for row in rows
    ]


def _indexes_for_table(cur: sqlite3.Cursor, table: str) -> list[dict[str, Any]]:
    rows = cur.execute(f"PRAGMA index_list({table})").fetchall()
    payload = []
    for row in rows:
        index_name = str(row[1])
        cols = [str(item[2]) for item in cur.execute(f"PRAGMA index_info({index_name})").fetchall()]
        payload.append(
            {
                "name": index_name,
                "unique": bool(row[2]),
                "columns": cols,
                "origin": row[3],
                "partial": bool(row[4]) if len(row) > 4 else False,
            }
        )
    return payload


def audit_schema() -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        tables = _table_names(cur)
        indexes = _index_names(cur)
        table_map = {table: {"columns": _table_columns(cur, table), "indexes": _indexes_for_table(cur, table)} for table in tables}
        compatibility: dict[str, Any] = {}
        missing_tables = []
        critical_issues = []

        for table_name, spec in REQUIRED_TABLES.items():
            table_payload = table_map.get(table_name)
            if table_payload is None:
                missing_tables.append(table_name)
                critical_issues.append(f"missing table: {table_name}")
                compatibility[table_name] = {"exists": False}
                continue
            column_names = [item["name"] for item in table_payload["columns"]]
            pk_columns = [item["name"] for item in table_payload["columns"] if int(item.get("pk") or 0) > 0]
            user_scope_column = next((column for column in spec["user_columns"] if column in column_names), None)
            date_columns = [column for column in spec["date_columns"] if column in column_names]
            unique_hits = [column for column in spec["unique_columns"] if column in pk_columns]
            for index in table_payload["indexes"]:
                if index["unique"]:
                    for column in spec["unique_columns"]:
                        if column in (index["columns"] or []):
                            unique_hits.append(column)
            compatibility[table_name] = {
                "exists": True,
                "user_scope_column": user_scope_column,
                "date_columns": date_columns,
                "unique_upsert_columns": sorted(set(unique_hits)),
                "indexes": [item["name"] for item in table_payload["indexes"]],
            }
            if user_scope_column is None:
                critical_issues.append(f"{table_name}: missing user scope column")
            if not date_columns:
                critical_issues.append(f"{table_name}: missing date column")
            if not unique_hits and table_name not in ("sync_state",):
                critical_issues.append(f"{table_name}: missing unique upsert key")

        return {
            "db_name": DB_NAME,
            "tables": table_map,
            "table_names": tables,
            "index_names": indexes,
            "compatibility": compatibility,
            "missing_tables": missing_tables,
            "critical_issues": critical_issues,
            "is_compatible": not critical_issues,
        }
    finally:
        conn.close()


def _print_schema_report(report: dict[str, Any]) -> None:
    print(f"DB: {report['db_name']}")
    print()
    print("TABLES")
    for table_name in report["table_names"]:
        print(f"- {table_name}")
        for column in report["tables"][table_name]["columns"]:
            suffix = " PK" if int(column["pk"] or 0) else ""
            print(f"  column {column['name']} {column['type']}{suffix}")
        for index in report["tables"][table_name]["indexes"]:
            unique_flag = " UNIQUE" if index["unique"] else ""
            print(f"  index {index['name']}{unique_flag}: {', '.join(index['columns'])}")
    print()
    print("COMPATIBILITY")
    for table_name, payload in report["compatibility"].items():
        print(f"- {table_name}:")
        if not payload.get("exists"):
            print("  exists: no")
            continue
        print(f"  user_scope_column: {payload.get('user_scope_column') or '-'}")
        print(f"  date_columns: {', '.join(payload.get('date_columns') or []) or '-'}")
        print(f"  unique_upsert_columns: {', '.join(payload.get('unique_upsert_columns') or []) or '-'}")
    print()
    print("SUMMARY")
    print(f"is_compatible: {report['is_compatible']}")
    print(f"missing_tables: {json.dumps(report['missing_tables'], ensure_ascii=False)}")
    print(f"critical_issues: {json.dumps(report['critical_issues'], ensure_ascii=False)}")


def main() -> int:
    report = audit_schema()
    _print_schema_report(report)
    return 0 if report["is_compatible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
