from __future__ import annotations

import importlib
import os
import tempfile


def test_ads_cooldown_creates_queue_and_worker_retries(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        import vooglii_telegram.services.sync_service as sync_service
        import vooglii_wb_sync.sync_orchestrator as orchestrator
        import vooglii_wb_sync.sync_queue as sync_queue
        import vooglii_wb_sync.sync_state as sync_state

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(sync_queue)
        importlib.reload(sync_state)
        importlib.reload(orchestrator)
        importlib.reload(sync_service)

        monkeypatch.setattr(orchestrator, "resolve_sync_token", lambda *_args, **_kwargs: type("Token", (), {"token": "t", "source": "test", "reason": None})())
        monkeypatch.setattr(orchestrator, "sync_sales", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "sales", "source_rows": 2, "inserted": 2, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_orders", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "orders", "source_rows": 1, "inserted": 1, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_finance", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "finance", "source_rows": 5, "inserted": 5, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_stocks", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "stocks", "source_rows": 3, "inserted": 3, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "refresh_products_index", lambda *_args, **_kwargs: {"raw_status": "MISSING_COST_VALUES", "inserted": 4, "updated": 0, "skipped": 0, "invalid": 0, "source_rows": 4, "meta": {}})

        ads_state = {"attempt": 0}

        def _ads_loader(*_args, **_kwargs):
            ads_state["attempt"] += 1
            if ads_state["attempt"] == 1:
                return {"raw_status": "ADS_COOLDOWN:300", "source_name": "ads", "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}}
            return {"raw_status": "SUCCESS", "source_name": "ads", "source_rows": 19, "inserted": 19, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}}

        monkeypatch.setattr(orchestrator, "sync_advertising", _ads_loader)
        monkeypatch.setattr(orchestrator, "next_allowed_at", lambda _user_id, block: "2026-07-07 20:21:15" if block == "advertising" else None)
        monkeypatch.setattr(sync_service, "run_post_sync_rebuild", lambda *_args, **_kwargs: {"status": "OK"})

        result = orchestrator.run_sync(42, token="t", days=30)

        assert result["blocks"]["advertising"]["status"] == "API_LIMIT"
        queued = sync_queue.list_user_sync_queue(42)
        assert len(queued) == 1
        assert queued[0]["status"] == sync_queue.QUEUE_WAIT_LIMIT
        assert queued[0]["block"] == "advertising"

        worker = sync_service.run_sync_queue_worker(now="2026-07-07 20:21:15")
        assert worker["claimed"] == 1

        queue_after = sync_queue.list_user_sync_queue(42, include_completed=True)
        assert queue_after[0]["status"] == sync_queue.QUEUE_DONE
        state = sync_state.list_sync_state(42)
        assert state["advertising"]["status"] == "OK"


def test_failed_block_does_not_break_other_blocks(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        import vooglii_wb_sync.sync_orchestrator as orchestrator

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(orchestrator)

        monkeypatch.setattr(orchestrator, "resolve_sync_token", lambda *_args, **_kwargs: type("Token", (), {"token": "t", "source": "test", "reason": None})())
        monkeypatch.setattr(orchestrator, "sync_sales", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "sales", "source_rows": 2, "inserted": 2, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_orders", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "orders", "source_rows": 1, "inserted": 1, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_finance", lambda *_args, **_kwargs: {"raw_status": "EXCEPTION:Timeout", "source_name": "finance", "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_advertising", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "ads", "source_rows": 9, "inserted": 9, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "sync_stocks", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "source_name": "stocks", "source_rows": 3, "inserted": 3, "updated": 0, "skipped": 0, "invalid": 0, "meta": {}})
        monkeypatch.setattr(orchestrator, "refresh_products_index", lambda *_args, **_kwargs: {"raw_status": "SUCCESS", "inserted": 4, "updated": 0, "skipped": 0, "invalid": 0, "source_rows": 4, "meta": {}})
        monkeypatch.setattr(orchestrator, "next_allowed_at", lambda *_args, **_kwargs: None)

        result = orchestrator.run_sync(42, token="t", days=30)

        assert result["blocks"]["sales"]["status"] == "OK"
        assert result["blocks"]["orders"]["status"] == "OK"
        assert result["blocks"]["finance"]["status"] == "ERROR"
        assert result["blocks"]["advertising"]["status"] == "OK"
        assert result["blocks"]["stocks"]["status"] == "OK"

