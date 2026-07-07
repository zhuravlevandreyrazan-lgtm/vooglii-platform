from pathlib import Path
import importlib
import os
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.backfill_financial_period as backfill_script
from vooglii_telegram.services.token_resolver import TokenResolution


def test_backfill_no_token_reports_precise_reason(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(backfill_script)

        monkeypatch.setattr(
            backfill_script,
            "resolve_wb_token",
            lambda _user_id: TokenResolution(token=None, source="missing", encrypted=False, reason="no token source available"),
        )
        monkeypatch.setattr(
            backfill_script,
            "get_user",
            lambda user_id: (user_id, "tester", None, "PRO", 1, None, None, "owner", "2026-08-09", None, None),
        )

        result = backfill_script._run_backfill(658486226, "2026-06-01", "2026-06-30", "wb-api")

        assert result["api_blocks"]["token"]["status"] == "WB_API_UNAVAILABLE_FOR_PERIOD:NO_TOKEN"
        assert result["api_blocks"]["token"]["token_source"] == "missing"


if __name__ == "__main__":
    test_backfill_no_token_reports_precise_reason(__import__("pytest").MonkeyPatch())
    print("WB SYNC BACKFILL PARTIAL OK", flush=True)
