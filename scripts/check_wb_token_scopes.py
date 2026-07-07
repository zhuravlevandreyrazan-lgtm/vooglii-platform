from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_NAME, WB_TOKEN


EXPECTED_SCOPES = (
    "statistics",
    "analytics",
    "promotion/advertising",
    "finance",
    "content/products",
    "stocks",
)


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_scopes(raw_value: Any) -> list[str]:
    text = str(raw_value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        items: list[str] = []
        for key, value in parsed.items():
            if value:
                items.append(str(key).strip())
        return [item for item in items if item]
    return [item.strip() for item in text.replace(";", ",").split(",") if item.strip()]


def build_scope_report(user_id: int, db_path: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "user_id": int(user_id),
        "db_path": db_path or DB_NAME,
        "users_token_present": False,
        "users_token_length": 0,
        "wb_cabinets_rows": [],
        "config_token_present": bool(str(WB_TOKEN or "").strip()),
        "resolved_source": "missing",
        "resolved_reason": "no token source available",
        "scopes": {
            scope_name: {
                "granted": False,
                "source": None,
            }
            for scope_name in EXPECTED_SCOPES
        },
        "notes": [],
    }
    conn = _connect(db_path)
    try:
        user_row = conn.execute(
            "SELECT telegram_id, username, wb_token FROM users WHERE telegram_id=?",
            (int(user_id),),
        ).fetchone()
        if user_row:
            token_text = str(user_row["wb_token"] or "").strip()
            report["users_token_present"] = bool(token_text)
            report["users_token_length"] = len(token_text)
            if token_text:
                report["resolved_source"] = "users.wb_token"
                report["resolved_reason"] = None
        else:
            report["notes"].append("users row not found")

        try:
            cabinet_rows = conn.execute(
                """
                SELECT
                    id,
                    name,
                    connected,
                    status,
                    scopes,
                    seller_token_encrypted,
                    statistics_token_encrypted,
                    advertising_token_encrypted,
                    finance_token_encrypted,
                    updated_at,
                    last_checked_at,
                    last_sync_at
                FROM wb_cabinets
                WHERE data_owner_id=?
                ORDER BY connected DESC, updated_at DESC, created_at DESC
                """,
                (int(user_id),),
            ).fetchall()
        except sqlite3.OperationalError:
            cabinet_rows = []
            report["notes"].append("wb_cabinets table unavailable")

        for row in cabinet_rows:
            scopes = _parse_scopes(row["scopes"])
            token_columns = {
                "seller": bool(str(row["seller_token_encrypted"] or "").strip()),
                "statistics": bool(str(row["statistics_token_encrypted"] or "").strip()),
                "advertising": bool(str(row["advertising_token_encrypted"] or "").strip()),
                "finance": bool(str(row["finance_token_encrypted"] or "").strip()),
            }
            report["wb_cabinets_rows"].append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "connected": int(row["connected"] or 0),
                    "status": row["status"],
                    "scopes_raw": row["scopes"],
                    "scopes": scopes,
                    "token_columns": token_columns,
                    "updated_at": row["updated_at"],
                    "last_checked_at": row["last_checked_at"],
                    "last_sync_at": row["last_sync_at"],
                }
            )
            if report["resolved_source"] == "missing" and any(token_columns.values()):
                report["resolved_source"] = "wb_cabinets"
                report["resolved_reason"] = None
            for scope_name in scopes:
                if scope_name in report["scopes"]:
                    report["scopes"][scope_name]["granted"] = True
                    report["scopes"][scope_name]["source"] = "wb_cabinets.scopes"

        if report["resolved_source"] == "missing" and report["config_token_present"]:
            report["resolved_source"] = "config.WB_TOKEN"
            report["resolved_reason"] = None

        if not report["wb_cabinets_rows"]:
            report["notes"].append("no wb_cabinets rows for user")
        if not report["users_token_present"]:
            report["notes"].append("users.wb_token is empty")
        if not report["config_token_present"]:
            report["notes"].append("config.WB_TOKEN is empty")
        if report["resolved_source"] == "missing":
            report["notes"].append("live WB sync cannot run until a token is stored again")
    finally:
        conn.close()
    return report


def _print_report(report: dict[str, Any]) -> None:
    print(f"user_id: {report['user_id']}")
    print(f"db_path: {report['db_path']}")
    print(f"resolved_source: {report['resolved_source']}")
    print(f"resolved_reason: {report.get('resolved_reason') or '-'}")
    print(f"users_token_present: {report['users_token_present']}")
    print(f"users_token_length: {report['users_token_length']}")
    print(f"config_token_present: {report['config_token_present']}")
    print()
    print("expected_scopes:")
    for scope_name in EXPECTED_SCOPES:
        item = report["scopes"][scope_name]
        print(
            f"- {scope_name}: granted={item['granted']} source={item.get('source') or '-'}"
        )
    print()
    print("wb_cabinets:")
    rows = report.get("wb_cabinets_rows") or []
    if not rows:
        print("- none")
    else:
        for row in rows:
            print(
                f"- id={row['id']} connected={row['connected']} status={row['status']} "
                f"scopes={','.join(row['scopes']) or '-'} "
                f"tokens="
                f"statistics:{row['token_columns']['statistics']},"
                f"advertising:{row['token_columns']['advertising']},"
                f"finance:{row['token_columns']['finance']},"
                f"seller:{row['token_columns']['seller']}"
            )
    print()
    print("notes:")
    for note in report.get("notes") or ["none"]:
        print(f"- {note}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=int)
    args = parser.parse_args()
    report = build_scope_report(args.user_id)
    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
