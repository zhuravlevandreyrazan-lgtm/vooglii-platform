from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

import config
from db_manager import init_db


@dataclass
class BlockSyncState:
    telegram_id: int
    sync_block: str
    status: str
    status_reason: str | None = None
    last_success_at: str | None = None
    next_allowed_at: str | None = None
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_invalid: int = 0
    source_rows: int = 0
    source_name: str | None = None
    updated_at: str | None = None
    meta_json: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "telegram_id": self.telegram_id,
            "sync_block": self.sync_block,
            "status": self.status,
            "status_reason": self.status_reason,
            "last_success_at": self.last_success_at,
            "next_allowed_at": self.next_allowed_at,
            "rows_inserted": int(self.rows_inserted or 0),
            "rows_updated": int(self.rows_updated or 0),
            "rows_skipped": int(self.rows_skipped or 0),
            "rows_invalid": int(self.rows_invalid or 0),
            "source_rows": int(self.source_rows or 0),
            "source_name": self.source_name,
            "updated_at": self.updated_at,
        }
        if self.meta_json:
            try:
                payload["meta"] = json.loads(self.meta_json)
            except Exception:
                payload["meta"] = self.meta_json
        return payload


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def save_sync_state(
    telegram_id: int,
    sync_block: str,
    status: str,
    *,
    status_reason: str | None = None,
    last_success_at: str | None = None,
    next_allowed_at: str | None = None,
    rows_inserted: int = 0,
    rows_updated: int = 0,
    rows_skipped: int = 0,
    rows_invalid: int = 0,
    source_rows: int = 0,
    source_name: str | None = None,
    meta: dict[str, Any] | None = None,
    updated_at: str | None = None,
) -> None:
    conn = _connect()
    try:
        now = updated_at or __import__("load_sales")._now_str()
        conn.execute(
            """
            INSERT INTO sync_state(
                telegram_id, sync_block, status, status_reason, last_success_at, next_allowed_at,
                rows_inserted, rows_updated, rows_skipped, rows_invalid, source_rows, source_name,
                updated_at, meta_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(telegram_id, sync_block) DO UPDATE SET
                status=excluded.status,
                status_reason=excluded.status_reason,
                last_success_at=excluded.last_success_at,
                next_allowed_at=excluded.next_allowed_at,
                rows_inserted=excluded.rows_inserted,
                rows_updated=excluded.rows_updated,
                rows_skipped=excluded.rows_skipped,
                rows_invalid=excluded.rows_invalid,
                source_rows=excluded.source_rows,
                source_name=excluded.source_name,
                updated_at=excluded.updated_at,
                meta_json=excluded.meta_json
            """,
            (
                int(telegram_id),
                str(sync_block),
                str(status),
                status_reason,
                last_success_at,
                next_allowed_at,
                int(rows_inserted or 0),
                int(rows_updated or 0),
                int(rows_skipped or 0),
                int(rows_invalid or 0),
                int(source_rows or 0),
                source_name,
                now,
                json.dumps(meta or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_sync_state(telegram_id: int, sync_block: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM sync_state WHERE telegram_id=? AND sync_block=?",
            (int(telegram_id), str(sync_block)),
        ).fetchone()
        if not row:
            return None
        return BlockSyncState(**dict(row)).as_dict()
    finally:
        conn.close()


def list_sync_state(telegram_id: int) -> dict[str, dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM sync_state WHERE telegram_id=? ORDER BY sync_block",
            (int(telegram_id),),
        ).fetchall()
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = BlockSyncState(**dict(row)).as_dict()
            result[item["sync_block"]] = item
        return result
    finally:
        conn.close()
