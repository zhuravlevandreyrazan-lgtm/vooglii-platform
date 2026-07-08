from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
from vooglii_validation.wb_weekly_snapshot import build_wb_weekly_snapshot_dict


FIELDS = (
    "wb_sale_amount",
    "wb_payout_amount",
    "wb_total_to_pay",
    "wb_logistics",
    "wb_storage",
    "wb_deductions",
    "wb_acquiring",
    "advertising",
    "cost_price",
    "operational_profit",
)


def _money(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}".replace(",", " ")


def _surface_values(name: str, payload: dict) -> dict[str, object]:
    return {field_name: payload.get(field_name) for field_name in FIELDS}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit customer snapshot consistency across Telegram customer surfaces.")
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    days = (args.date_from, args.date_to)
    period_from = date.fromisoformat(args.date_from)
    period_to = date.fromisoformat(args.date_to)
    snapshot = telegram_bot._customer_financial_snapshot(args.user_id, days)
    wb_weekly_snapshot = None
    closed_period_mismatches: list[str] = []
    failures: list[str] = []
    if str(snapshot.get("source_mode") or "") == "WB_NATIVE_CLOSED":
        wb_weekly_snapshot = build_wb_weekly_snapshot_dict(args.user_id, period_from, period_to)
        for field_name in (
            "wb_sale_amount",
            "wb_payout_amount",
            "wb_total_to_pay",
            "wb_logistics",
            "wb_storage",
            "wb_acquiring",
            "wb_deductions",
            "wb_other",
        ):
            customer_value = snapshot.get(field_name)
            weekly_value = wb_weekly_snapshot.get(field_name)
            if customer_value != weekly_value:
                closed_period_mismatches.append(
                    f"{field_name}: customer_snapshot={_money(customer_value)} wb_weekly_snapshot={_money(weekly_value)}"
                )
        for field_name in ("wb_logistics", "wb_storage", "wb_total_to_pay"):
            trace = dict((snapshot.get("field_trace") or {}).get(field_name) or {})
            selected_source = str(trace.get("selected_source") or "")
            if selected_source.startswith("finance_raw_audit"):
                failures.append(f"{field_name}: FAIL source={selected_source}")
        if snapshot.get("wb_total_to_pay") == snapshot.get("wb_payout_amount") and snapshot.get("wb_total_to_pay") is not None:
            failures.append("wb_total_to_pay: FAIL equals wb_payout_amount")
    surfaces = {
        "Snapshot": telegram_bot._customer_financial_values(snapshot),
        "Home": _surface_values("Home", telegram_bot._home_snapshot(args.user_id, days)),
        "Business": _surface_values("Business", telegram_bot._business_center_snapshot(args.user_id, days)),
        "Finance": _surface_values("Finance", telegram_bot._finance_center_snapshot(args.user_id, days)),
        "Report": _surface_values("Report", telegram_bot._customer_report_snapshot(args.user_id, days)),
        "PNL": _surface_values("PNL", telegram_bot._customer_pnl_snapshot(args.user_id, days)),
        "Dashboard": _surface_values("Dashboard", telegram_bot._customer_dashboard_snapshot(args.user_id, days)),
    }

    print(f"Customer Snapshot Consistency Audit: {args.date_from}..{args.date_to}")
    print("")
    for field_name in FIELDS:
        expected = surfaces["Snapshot"][field_name]
        print(field_name)
        print("-" * len(field_name))
        for surface_name, values in surfaces.items():
            value = values.get(field_name)
            status = "OK" if value == expected else "MISMATCH"
            print(f"{surface_name:10} {status:8} {_money(value)}")
        print("")
    if wb_weekly_snapshot is not None:
        print("WB Weekly Snapshot Alignment")
        print("--------------------------")
        if closed_period_mismatches:
            for mismatch in closed_period_mismatches:
                print(f"MISMATCH {mismatch}")
        else:
            print("OK customer_snapshot matches wb_weekly_snapshot selected values")
        print("")
    if failures:
        print("FAIL")
        print("----")
        for item in failures:
            print(item)
        print("")
    return 1 if closed_period_mismatches or failures else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
