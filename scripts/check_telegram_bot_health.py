from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import BOT_TOKEN, DB_NAME
from db_manager import init_db


def main() -> int:
    if not str(BOT_TOKEN or "").strip():
        raise RuntimeError("BOT_TOKEN is not configured.")

    init_db()
    db_path = Path(DB_NAME)
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database is missing: {db_path}")

    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("SELECT 1")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
