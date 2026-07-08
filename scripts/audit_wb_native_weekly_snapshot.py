from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot


FIELD_ORDER = (
    "wb_sale_amount",
    "wb_payout_amount",
    "wb_logistics",
    "wb_storage",
    "wb_acquiring",
    "wb_deductions",
    "wb_total_to_pay",
    "wb_other",
    "penalties",
    "advertising",
)


def _money(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}".replace(",", " ")


def _print_section(title: str) -> None:
    print(title)
    print("-" * len(title))


def _print_candidate(prefix: str, item: dict) -> None:
    print(f"{prefix}source_table: {item.get('source_table') or '-'}")
    print(f"{prefix}source_column: {item.get('source_column') or '-'}")
    print(f"{prefix}source_filter: {item.get('source_filter') or '-'}")
    print(f"{prefix}row_count: {int(item.get('rows') or 0)}")
    print(f"{prefix}sum: {_money(item.get('value'))}")
    print(f"{prefix}min_date: {item.get('source_min_date') or '-'}")
    print(f"{prefix}max_date: {item.get('source_max_date') or '-'}")
    breakdown = item.get("breakdown") or {}
    if breakdown:
        print(f"{prefix}reason_breakdown: {json.dumps(breakdown, ensure_ascii=False, sort_keys=True)}")
    else:
        print(f"{prefix}reason_breakdown: -")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit WB-native weekly snapshot mapping.")
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    snapshot = build_wb_weekly_snapshot(args.user_id, date.fromisoformat(args.date_from), date.fromisoformat(args.date_to))

    _print_section("snapshot totals")
    for field_name in FIELD_ORDER:
        print(f"{field_name}: {_money(getattr(snapshot, field_name, None))}")

    for field_name in FIELD_ORDER:
        details = dict((snapshot.source_map or {}).get(field_name) or {})
        _print_section(field_name)
        print(f"selected_source: {details.get('selected_source') or '-'}")
        print(f"selected_value: {_money(details.get('selected_value'))}")
        _print_candidate("", details)
        for index, candidate in enumerate(list(details.get("candidates") or []), 1):
            print("")
            print(f"candidate_{index}: {candidate.get('source') or '-'}")
            _print_candidate("  ", dict(candidate or {}))

    if snapshot.warnings:
        _print_section("warnings")
        for warning in snapshot.warnings:
            print(warning)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
