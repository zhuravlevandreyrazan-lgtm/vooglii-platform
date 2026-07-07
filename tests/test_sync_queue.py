from __future__ import annotations

import sqlite3

import config
import db_manager
import vooglii_wb_sync.sync_queue as sync_queue


def _prepare_db(tmp_path):
    db_path = str(tmp_path / "sync-queue.sqlite")
    config.DB_NAME = db_path
    db_manager.DB_NAME = db_path
    sync_queue.DB_NAME = db_path
    db_manager.init_db()
    return db_path


def test_sync_queue_deduplicates_active_tasks_and_claims_ready(tmp_path):
    _prepare_db(tmp_path)

    first = sync_queue.enqueue_sync_task(
        42,
        "advertising",
        "2026-07-01",
        "2026-07-31",
        status=sync_queue.QUEUE_WAIT_LIMIT,
        run_after="2026-07-07 20:21:15",
        last_error="ADS_COOLDOWN:120",
    )
    second = sync_queue.enqueue_sync_task(
        42,
        "advertising",
        "2026-07-01",
        "2026-07-31",
        status=sync_queue.QUEUE_WAIT_LIMIT,
        run_after="2026-07-07 20:25:00",
        last_error="ADS_COOLDOWN:360",
    )

    assert first["id"] == second["id"]
    queued = sync_queue.list_user_sync_queue(42)
    assert len(queued) == 1
    assert queued[0]["run_after"] == "2026-07-07 20:25:00"

    claimed_early = sync_queue.claim_ready_tasks(now="2026-07-07 20:24:59")
    assert claimed_early == []

    claimed = sync_queue.claim_ready_tasks(now="2026-07-07 20:25:00")
    assert len(claimed) == 1
    assert claimed[0]["status"] == sync_queue.QUEUE_RUNNING
    assert claimed[0]["attempts"] == 1


def test_wait_limit_without_run_after_gets_default_policy(tmp_path):
    _prepare_db(tmp_path)

    queued = sync_queue.enqueue_sync_task(
        42,
        "sales",
        "2026-07-01",
        "2026-07-31",
        status=sync_queue.QUEUE_WAIT_LIMIT,
        run_after=None,
        last_error="RATE_LIMIT",
    )

    assert queued["run_after"]
    assert queued["run_after"] != "-"
