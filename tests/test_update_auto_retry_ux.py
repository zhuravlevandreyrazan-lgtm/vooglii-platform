from __future__ import annotations

import importlib
import os
import tempfile


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def test_update_text_and_sync_views_show_moscow_time():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        import vooglii_telegram.services.sync_service as sync_service
        import vooglii_wb_sync.sync_queue as sync_queue
        import vooglii_wb_sync.sync_state as sync_state

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(sync_queue)
        importlib.reload(sync_state)
        importlib.reload(sync_service)

        sync_state.save_sync_state(42, "sales", "OK", status_reason="SUCCESS", last_success_at="2026-07-07 15:49:00", source_rows=233)
        sync_state.save_sync_state(42, "orders", "OK", status_reason="SUCCESS", last_success_at="2026-07-07 15:50:00", source_rows=111)
        sync_state.save_sync_state(42, "finance", "OK", status_reason="SUCCESS", last_success_at="2026-07-07 15:50:00", source_rows=1158)
        sync_state.save_sync_state(
            42,
            "advertising",
            "API_LIMIT",
            status_reason="ADS_COOLDOWN:300",
            next_allowed_at="2026-07-07 20:21:15",
            meta={"retry_source": "cooldown", "retry_seconds": 300, "retry_is_approximate": False},
        )
        sync_state.save_sync_state(42, "stocks", "OK", status_reason="SUCCESS", last_success_at="2026-07-07 15:50:00", source_rows=77)
        sync_state.save_sync_state(42, "products", "OK", status_reason="SUCCESS", last_success_at="2026-07-07 15:50:00", source_rows=45)
        sync_state.save_sync_state(42, "cost", "PARTIAL", status_reason="MISSING_COST_VALUES", last_success_at=None, source_rows=45)
        sync_queue.enqueue_sync_task(
            42,
            "advertising",
            "2026-07-01",
            "2026-07-31",
            status=sync_queue.QUEUE_WAIT_LIMIT,
            run_after="2026-07-07 20:21:15",
            last_error="ADS_COOLDOWN:300 retry_source=cooldown",
        )
        sync_queue.record_sync_history(42, "sales", "OK", source_rows=233, message="SUCCESS")
        sync_queue.record_sync_history(42, "finance", "OK", source_rows=1158, message="SUCCESS")
        sync_queue.record_sync_history(
            42,
            "advertising",
            "API_LIMIT",
            source_rows=0,
            retry_at="2026-07-07 20:21:15",
            message="ADS_COOLDOWN:300 retry_source=cooldown",
        )

        update_text = sync_service.format_sync_result(
            {
                "saved": 0,
                "overall_status": "PARTIAL",
                "blocks": {
                    "sales": {"status": "OK", "raw_status": "SUCCESS"},
                    "orders": {"status": "OK", "raw_status": "SUCCESS"},
                    "finance": {"status": "OK", "raw_status": "SUCCESS"},
                    "advertising": {
                        "status": "API_LIMIT",
                        "raw_status": "ADS_COOLDOWN:300",
                        "next_allowed_at": "2026-07-07 20:21:15",
                        "meta": {"retry_source": "cooldown", "retry_seconds": 300, "retry_is_approximate": False},
                    },
                    "stocks": {"status": "OK", "raw_status": "SUCCESS"},
                    "products": {"status": "OK", "raw_status": "SUCCESS"},
                    "cost": {"status": "PARTIAL", "raw_status": "MISSING_COST_VALUES"},
                },
            }
        )
        status_text = sync_service.build_sync_status_text(42)
        history_text = sync_service.build_sync_history_text(42)

        _assert("Автоматически повторю после 20:21 МСК" in update_text, "update text should show retry time in MSK")
        _assert("UTC" not in update_text, "update text should not leak UTC")
        _assert("Следующая попытка: 20:21 МСК" in status_text, "sync status should show next retry in MSK")
        _assert("20:21 МСК" in history_text, "sync history should show retry time in MSK")


def test_wait_limit_without_exact_cooldown_shows_approximate_retry():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        import vooglii_telegram.services.sync_service as sync_service
        import vooglii_wb_sync.sync_queue as sync_queue
        import vooglii_wb_sync.sync_state as sync_state

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(sync_queue)
        importlib.reload(sync_state)
        importlib.reload(sync_service)

        sync_state.save_sync_state(
            42,
            "sales",
            "API_LIMIT",
            status_reason="RATE_LIMIT",
            next_allowed_at="2026-07-08 10:10:00",
            meta={"retry_source": "default_policy", "retry_seconds": 600, "retry_is_approximate": True},
        )
        sync_queue.enqueue_sync_task(
            42,
            "sales",
            "2026-07-01",
            "2026-07-31",
            status=sync_queue.QUEUE_WAIT_LIMIT,
            run_after="2026-07-08 10:10:00",
            last_error="RATE_LIMIT retry_source=default_policy",
        )
        sync_queue.record_sync_history(
            42,
            "sales",
            "API_LIMIT",
            source_rows=0,
            retry_at="2026-07-08 10:10:00",
            message="RATE_LIMIT retry_source=default_policy",
        )

        update_text = sync_service.format_sync_result(
            {
                "saved": 0,
                "overall_status": "PARTIAL",
                "blocks": {
                    "sales": {
                        "status": "API_LIMIT",
                        "raw_status": "RATE_LIMIT",
                        "next_allowed_at": "2026-07-08 10:10:00",
                        "meta": {"retry_source": "default_policy", "retry_seconds": 600, "retry_is_approximate": True},
                    }
                },
            }
        )
        status_text = sync_service.build_sync_status_text(42)
        history_text = sync_service.build_sync_history_text(42)

        _assert("примерно в 10:10 МСК" in update_text, "update text should show approximate retry time")
        _assert("Следующая попытка: примерно в 10:10 МСК" in status_text, "sync status should show approximate retry time")
        _assert("retry примерно в 10:10 МСК" in history_text, "sync history should show approximate retry time")
        _assert("Следующая попытка: -" not in status_text, "sync status should never show missing retry time")
        _assert("retry -" not in history_text, "sync history should never show missing retry time")


if __name__ == "__main__":
    test_update_text_and_sync_views_show_moscow_time()
    test_wait_limit_without_exact_cooldown_shows_approximate_retry()
    print("UPDATE AUTO RETRY UX OK", flush=True)
