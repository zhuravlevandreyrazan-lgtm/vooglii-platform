from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot


def _money(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}".replace(",", " ")


def _print_section(title: str) -> None:
    print(title)
    print("-" * len(title))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit WB weekly parity source coverage.")
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        _print_section("finance_raw_audit columns")
        for row in conn.execute("PRAGMA table_info(finance_raw_audit)").fetchall():
            print(f"{row['name']}: {row['type']}")

        numeric_fields = ["penalty", "deduction", "acceptance", "acceptance_fee", "additional_payment", "acquiring_fee"]
        _print_section("available numeric fields")
        for field in numeric_fields:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS rows_count, COALESCE(SUM(ABS(COALESCE({field}, 0))), 0) AS total_amount
                FROM finance_raw_audit
                WHERE telegram_id=? AND substr(report_date, 1, 10) BETWEEN ? AND ?
                """,
                (args.user_id, args.date_from, args.date_to),
            ).fetchone()
            print(f"{field}: rows={int(row['rows_count'] or 0)} total={_money(row['total_amount'])}")

        _print_section("available operation/type fields")
        rows = conn.execute(
            """
            SELECT COALESCE(operation_type, doc_type_name, payment_type, '-') AS field_value, COUNT(*) AS rows_count
            FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date, 1, 10) BETWEEN ? AND ?
            GROUP BY COALESCE(operation_type, doc_type_name, payment_type, '-')
            ORDER BY rows_count DESC, field_value ASC
            """,
            (args.user_id, args.date_from, args.date_to),
        ).fetchall()
        for row in rows[:30]:
            print(f"{row['field_value']}: {int(row['rows_count'] or 0)}")

        _print_section("sums by operation/type/reason")
        rows = conn.execute(
            """
            SELECT
                COALESCE(operation_type, '-') AS operation_type,
                COALESCE(doc_type_name, '-') AS doc_type_name,
                COALESCE(payment_type, '-') AS payment_type,
                COUNT(*) AS rows_count,
                COALESCE(SUM(ABS(COALESCE(deduction, 0))), 0) AS deductions,
                COALESCE(SUM(ABS(COALESCE(acquiring_fee, 0))), 0) AS acquiring,
                COALESCE(SUM(ABS(COALESCE(penalty, 0)) + ABS(COALESCE(acceptance, 0)) + ABS(COALESCE(acceptance_fee, 0)) + ABS(COALESCE(additional_payment, 0))), 0) AS other_total
            FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date, 1, 10) BETWEEN ? AND ?
            GROUP BY COALESCE(operation_type, '-'), COALESCE(doc_type_name, '-'), COALESCE(payment_type, '-')
            ORDER BY rows_count DESC, deductions DESC
            """,
            (args.user_id, args.date_from, args.date_to),
        ).fetchall()
        for row in rows[:30]:
            print(
                f"{row['operation_type']} | {row['doc_type_name']} | {row['payment_type']} | "
                f"rows={int(row['rows_count'] or 0)} | deductions={_money(row['deductions'])} | "
                f"acquiring={_money(row['acquiring'])} | other={_money(row['other_total'])}"
            )

        _print_section("sample rows")
        rows = conn.execute(
            """
            SELECT id, report_date, operation_type, doc_type_name, payment_type, raw_json
            FROM finance_raw_audit
            WHERE telegram_id=? AND substr(report_date, 1, 10) BETWEEN ? AND ?
            ORDER BY report_date ASC, id ASC
            LIMIT 10
            """,
            (args.user_id, args.date_from, args.date_to),
        ).fetchall()
        for row in rows:
            payload = str(row["raw_json"] or "")
            print(f"id={row['id']} date={row['report_date']} op={row['operation_type'] or '-'} doc={row['doc_type_name'] or '-'} type={row['payment_type'] or '-'}")
            print(payload[:300].replace("\n", " "))

        snapshot = build_wb_weekly_snapshot(args.user_id, date.fromisoformat(args.date_from), date.fromisoformat(args.date_to))
        _print_section("mapping coverage summary")
        print(f"source_rows: {json.dumps(snapshot.source_rows, ensure_ascii=False, sort_keys=True)}")
        for metric_name, details in snapshot.source_map.items():
            if not isinstance(details, dict) or "selected_source" not in details:
                continue
            print(
                f"{metric_name}: source={details.get('selected_source') or '-'} "
                f"value={details.get('selected_value')} rows={details.get('rows')}"
            )
        if snapshot.warnings:
            _print_section("warnings")
            for warning in snapshot.warnings:
                print(warning)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
