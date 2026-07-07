from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

import config
from db_manager import init_db
from .rate_limiter import resolve_retry_policy


QUEUE_PENDING = "PENDING"
QUEUE_RUNNING = "RUNNING"
QUEUE_DONE = "DONE"
QUEUE_WAIT_LIMIT = "WAIT_LIMIT"
QUEUE_FAILED = "FAILED"
QUEUE_CANCELLED = "CANCELLED"

ACTIVE_QUEUE_STATUSES = (QUEUE_PENDING, QUEUE_RUNNING, QUEUE_WAIT_LIMIT)

BLOCK_PRIORITY = {
    "sales": 10,
    "orders": 20,
    "finance": 30,
    "advertising": 40,
    "stocks": 50,
    "products": 60,
    "cost": 70,
}


@dataclass
class SyncQueueTask:
    id: int
    user_id: int
    block: str
    period_from: str
    period_to: str
    status: str
    priority: int
    run_after: str | None
    attempts: int
    last_error: str | None
    created_at: str | None
    updated_at: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": int(self.id),
            "user_id": int(self.user_id),
            "block": str(self.block),
            "period_from": self.period_from,
            "period_to": self.period_to,
            "status": self.status,
            "priority": int(self.priority or 0),
            "run_after": self.run_after,
            "attempts": int(self.attempts or 0),
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    import load_sales

    return load_sales._now_str()


def _row_to_task(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    return SyncQueueTask(**dict(row)).as_dict()


def enqueue_sync_task(
    user_id: int,
    block: str,
    period_from: str,
    period_to: str,
    *,
    status: str = QUEUE_PENDING,
    priority: int | None = None,
    run_after: str | None = None,
    last_error: str | None = None,
) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        if str(status or "") == QUEUE_WAIT_LIMIT and not run_after:
            retry_policy = resolve_retry_policy(int(user_id), str(block), last_error)
            run_after = str(retry_policy.get("retry_at") or "")
        row = cur.execute(
            f"""
            SELECT *
            FROM sync_queue
            WHERE user_id=? AND block=? AND period_from=? AND period_to=?
              AND status IN ({",".join("?" for _ in ACTIVE_QUEUE_STATUSES)})
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(user_id), str(block), str(period_from), str(period_to), *ACTIVE_QUEUE_STATUSES),
        ).fetchone()
        now = _now()
        next_status = str(status or QUEUE_PENDING)
        next_priority = int(priority if priority is not None else BLOCK_PRIORITY.get(str(block), 100))
        if row:
            cur.execute(
                """
                UPDATE sync_queue
                SET status=?, priority=?, run_after=?, last_error=?, updated_at=?
                WHERE id=?
                """,
                (next_status, next_priority, run_after, last_error, now, int(row["id"])),
            )
            conn.commit()
            updated = cur.execute("SELECT * FROM sync_queue WHERE id=?", (int(row["id"]),)).fetchone()
            return _row_to_task(updated) or {}
        cur.execute(
            """
            INSERT INTO sync_queue(
                user_id, block, period_from, period_to, status, priority, run_after,
                attempts, last_error, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(user_id),
                str(block),
                str(period_from),
                str(period_to),
                next_status,
                next_priority,
                run_after,
                0,
                last_error,
                now,
                now,
            ),
        )
        conn.commit()
        created = cur.execute("SELECT * FROM sync_queue WHERE id=?", (int(cur.lastrowid),)).fetchone()
        return _row_to_task(created) or {}
    finally:
        conn.close()


def claim_ready_tasks(*, now: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.cursor()
        now_value = str(now or _now())
        conn.execute("BEGIN IMMEDIATE")
        rows = cur.execute(
            f"""
            SELECT *
            FROM sync_queue
            WHERE status IN (?, ?)
              AND COALESCE(run_after, created_at, '') <= ?
            ORDER BY priority ASC, COALESCE(run_after, created_at) ASC, id ASC
            LIMIT ?
            """,
            (QUEUE_PENDING, QUEUE_WAIT_LIMIT, now_value, int(limit)),
        ).fetchall()
        claimed: list[dict[str, Any]] = []
        for row in rows:
            cur.execute(
                """
                UPDATE sync_queue
                SET status=?, attempts=COALESCE(attempts,0)+1, updated_at=?
                WHERE id=?
                """,
                (QUEUE_RUNNING, now_value, int(row["id"])),
            )
            claimed_row = cur.execute("SELECT * FROM sync_queue WHERE id=?", (int(row["id"]),)).fetchone()
            task = _row_to_task(claimed_row)
            if task:
                claimed.append(task)
        conn.commit()
        return claimed
    finally:
        conn.close()


def update_sync_task(
    task_id: int,
    status: str,
    *,
    run_after: str | None = None,
    last_error: str | None = None,
) -> dict[str, Any] | None:
    conn = _connect()
    try:
        now = _now()
        existing = conn.execute("SELECT user_id, block, last_error FROM sync_queue WHERE id=?", (int(task_id),)).fetchone()
        if str(status or "") == QUEUE_WAIT_LIMIT and not run_after and existing:
            retry_policy = resolve_retry_policy(
                int(existing["user_id"]),
                str(existing["block"]),
                last_error or existing["last_error"],
                now=now,
            )
            run_after = str(retry_policy.get("retry_at") or "")
        conn.execute(
            """
            UPDATE sync_queue
            SET status=?, run_after=?, last_error=?, updated_at=?
            WHERE id=?
            """,
            (str(status), run_after, last_error, now, int(task_id)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM sync_queue WHERE id=?", (int(task_id),)).fetchone()
        return _row_to_task(row)
    finally:
        conn.close()


def list_user_sync_queue(user_id: int, *, include_completed: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        if include_completed:
            rows = conn.execute(
                """
                SELECT *
                FROM sync_queue
                WHERE user_id=?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (int(user_id), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT *
                FROM sync_queue
                WHERE user_id=? AND status IN ({",".join("?" for _ in ACTIVE_QUEUE_STATUSES)})
                ORDER BY priority ASC, COALESCE(run_after, created_at) ASC, id ASC
                LIMIT ?
                """,
                (int(user_id), *ACTIVE_QUEUE_STATUSES, int(limit)),
            ).fetchall()
        return [_row_to_task(row) or {} for row in rows]
    finally:
        conn.close()


def get_next_sync_task(user_id: int, block: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute(
            f"""
            SELECT *
            FROM sync_queue
            WHERE user_id=? AND block=? AND status IN ({",".join("?" for _ in ACTIVE_QUEUE_STATUSES)})
            ORDER BY priority ASC, COALESCE(run_after, created_at) ASC, id ASC
            LIMIT 1
            """,
            (int(user_id), str(block), *ACTIVE_QUEUE_STATUSES),
        ).fetchone()
        return _row_to_task(row)
    finally:
        conn.close()


def record_sync_history(
    user_id: int,
    block: str,
    status: str,
    *,
    source_rows: int = 0,
    retry_at: str | None = None,
    message: str | None = None,
) -> None:
    conn = _connect()
    try:
        now = _now()
        conn.execute(
            """
            INSERT INTO sync_history(
                user_id, block, status, source_rows, retry_at, message, created_at
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (
                int(user_id),
                str(block),
                str(status),
                int(source_rows or 0),
                retry_at,
                message,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_sync_history(user_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, user_id, block, status, source_rows, retry_at, message, created_at
            FROM sync_history
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
