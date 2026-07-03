from pathlib import Path
import importlib
import os
import sqlite3
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["DB_DIR"] = tmp_dir

        import config
        import db_manager

        importlib.reload(config)
        importlib.reload(db_manager)

        conn = db_manager.get_conn()
        try:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
        finally:
            conn.close()

        _assert(str(journal_mode).lower() == "wal", "journal_mode should be WAL")
        _assert(int(busy_timeout) >= 5000, "busy_timeout should be configured")
        _assert(int(synchronous) in (1, 2), "synchronous should be NORMAL-compatible")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("SQLITE SETTINGS OK", flush=True)
