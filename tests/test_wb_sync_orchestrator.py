from contextlib import redirect_stdout
import importlib
import io
import os
from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_orchestrator_persists_sync_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        import vooglii_wb_sync.sync_orchestrator as orchestrator
        import vooglii_wb_sync.sync_state as sync_state

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(sync_state)
        importlib.reload(orchestrator)

        monkeypatch.setattr(orchestrator, "resolve_sync_token", lambda *_args, **_kwargs: type("Token", (), {"token": "t", "source": "test", "reason": None})())
        monkeypatch.setattr(orchestrator, "sync_sales", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "sales", "source_rows": 2, "inserted": 2, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_orders", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "orders", "source_rows": 1, "inserted": 1, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_finance", lambda *_args, **_kwargs: {"raw_status": "RATE_LIMIT:60", "source_name": "finance", "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_payment_reports", lambda *_args, **_kwargs: {"raw_status": "NO_ROWS", "source_name": "payment_reports", "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_advertising", lambda *_args, **_kwargs: {"raw_status": "ADS_PARTIAL", "source_name": "ads", "source_rows": 3, "inserted": 3, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_stocks", lambda *_args, **_kwargs: {"raw_status": "WB_API_UNAVAILABLE_FOR_PERIOD", "source_name": "stocks", "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "refresh_products_index", lambda *_args, **_kwargs: {"inserted": 4, "updated": 0, "skipped": 0, "source_rows": 4})
        monkeypatch.setattr(orchestrator, "run_post_sync_rebuild", lambda *_args, **_kwargs: {"status": "OK"})
        monkeypatch.setattr(orchestrator, "next_allowed_at", lambda *_args, **_kwargs: "2026-07-07 12:00:00")

        result = orchestrator.run_sync(42, token="t", days=30)

        assert result["overall_status"] == "PARTIAL"
        state = sync_state.list_sync_state(42)
        assert state["sales"]["status"] == "OK"
        assert state["finance"]["status"] == "API_LIMIT"
        assert state["payment_reports"]["status"] == "NO_ROWS"
        assert state["advertising"]["status"] == "PARTIAL"
        assert state["stocks"]["status"] == "UNAVAILABLE"


if __name__ == "__main__":
    test_orchestrator_persists_sync_state(__import__("pytest").MonkeyPatch())
    print("WB SYNC ORCHESTRATOR OK", flush=True)
