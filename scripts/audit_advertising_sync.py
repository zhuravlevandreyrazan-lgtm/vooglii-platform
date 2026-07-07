from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.advertising_service import evaluate_advertising_sync_audit


def build_advertising_sync_audit(user_id: int, date_from: str, date_to: str) -> dict:
    return evaluate_advertising_sync_audit(int(user_id), str(date_from), str(date_to))


def _print_list(name: str, values: list[str]) -> None:
    print(f"{name}={','.join(values) if values else '-'}")


def _print_mapping(name: str, values: dict[str, object]) -> None:
    if not values:
        print(f"{name}=-")
        return
    pairs = [f"{key}:{values[key]}" for key in sorted(values)]
    print(f"{name}={'; '.join(pairs)}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    args = parser.parse_args()

    audit = build_advertising_sync_audit(args.user_id, args.date_from, args.date_to)

    print(f"requested_report_period={audit['requested_report_period']['date_from']}..{audit['requested_report_period']['date_to']}")
    print(f"sync_lookback_period={audit['sync_lookback_period']['date_from'] or '-'}..{audit['sync_lookback_period']['date_to'] or '-'}")
    print(f"raw_status={audit.get('raw_status') or '-'}")
    print(f"raw_normalized_status={audit.get('raw_normalized_status') or '-'}")
    _print_list("promotion_count_campaign_ids", list(audit.get("promotion_count_campaign_ids") or []))
    _print_list("fullstats_requested_ids", list(audit.get("fullstats_requested_ids") or []))
    _print_list("fullstats_returned_ids", list(audit.get("fullstats_returned_ids") or []))
    _print_list("missing_ids", list(audit.get("missing_ids") or []))
    print(f"campaigns_total={int(audit.get('campaigns_total') or 0)}")
    print(f"campaigns_returned={int(audit.get('campaigns_returned') or 0)}")
    print(f"campaigns_missing={int(audit.get('campaigns_missing') or 0)}")
    _print_mapping("local_rows_by_campaign", dict(audit.get("local_rows_by_campaign") or {}))
    _print_mapping("spend_by_campaign", dict(audit.get("spend_by_campaign") or {}))
    _print_mapping("days_by_campaign", dict(audit.get("days_by_campaign") or {}))
    print(f"report_period_rows_total={int(audit.get('report_period_rows_total') or 0)}")
    print(f"report_period_total_spend={float(audit.get('report_period_total_spend') or 0):.2f}")
    print(f"report_period_coverage_percent={float(audit.get('report_period_coverage_percent') or 0):.1f}")
    _print_list("report_period_missing_days", list(audit.get("report_period_missing_days") or []))
    print(f"campaign_coverage_status={audit.get('campaign_coverage_status') or '-'}")
    print(f"final_ads_status={audit.get('final_ads_status') or '-'}")
    print(f"final_ads_reason={audit.get('final_ads_reason') or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
