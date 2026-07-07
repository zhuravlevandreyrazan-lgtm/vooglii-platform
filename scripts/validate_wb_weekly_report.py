from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_validation import build_validation_report_text, load_wb_weekly_reference, validate_weekly_report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--file", required=True)
    parser.add_argument("--mode", default="weekly-parity", choices=["weekly-parity"])
    args = parser.parse_args()

    reference = load_wb_weekly_reference(str(args.file))
    result = validate_weekly_report(int(args.user_id), reference)

    print(f"mode: {args.mode}")
    print(f"reference period: {reference.period_from}..{reference.period_to}")
    print(f"reference hash: {reference.source_hash}")
    print(f"report number: {reference.report_number or '-'}")
    print(f"parity score: {result.parity_score:.1f}%")
    print(f"status: {result.status}")
    print()
    print(build_validation_report_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
