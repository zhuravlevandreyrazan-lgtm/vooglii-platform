from __future__ import annotations

import json
from datetime import datetime

from db_manager import get_conn, init_db


def log_audit_event(telegram_id: int | None, action: str, details: dict | str | None = None) -> None:
    init_db()
    payload = details if isinstance(details, str) else json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO audit_log(telegram_id,event_time,action,details) VALUES(?,?,?,?)",
            (
                int(telegram_id) if telegram_id is not None else None,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(action or "unknown"),
                payload,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def log_privileged_action(
    telegram_id: int,
    command: str,
    role: str,
    action: str,
    result: str,
    details: dict | None = None,
) -> None:
    log_audit_event(
        telegram_id,
        f"privileged:{action}",
        {
            "command": command,
            "role": role,
            "result": result,
            **dict(details or {}),
        },
    )

