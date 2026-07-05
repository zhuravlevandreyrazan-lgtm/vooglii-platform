from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_telegram.services.token_resolver import resolve_wb_token


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check safe WB token resolution without printing the token.")
    parser.add_argument("--user-id", required=True, type=int)
    args = parser.parse_args()

    resolution = resolve_wb_token(args.user_id)
    print(f"user_id: {args.user_id}")
    print(f"token_source: {resolution.source}")
    print(f"token_len: {resolution.token_len}")
    print(f"encrypted: {resolution.encrypted}")
    print(f"can_decrypt: {resolution.can_decrypt}")
    print(f"status: {resolution.status}")
    if resolution.reason:
        print(f"reason: {resolution.reason}")


if __name__ == "__main__":
    main()
