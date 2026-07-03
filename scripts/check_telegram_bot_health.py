from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import APP_ENV, BOT_TOKEN, DB_NAME
from db_manager import get_runtime_health, init_db
from security.token_crypto import validate_token_encryption_configuration


def main() -> int:
    if not str(BOT_TOKEN or "").strip():
        raise RuntimeError("BOT_TOKEN is not configured.")
    validate_token_encryption_configuration(require_in_production=True)

    init_db()
    db_path = Path(DB_NAME)
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database is missing: {db_path}")

    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("SELECT 1")
    finally:
        conn.close()
    if APP_ENV == "production":
        heartbeat = get_runtime_health("telegram-bot")
        if not heartbeat:
            raise RuntimeError("Telegram bot heartbeat is missing.")
        heartbeat_dt = datetime.strptime(str(heartbeat.get("last_heartbeat") or ""), "%Y-%m-%d %H:%M:%S")
        if datetime.now() - heartbeat_dt > timedelta(minutes=3):
            raise RuntimeError("Telegram bot heartbeat is stale.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
