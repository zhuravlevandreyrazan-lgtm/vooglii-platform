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
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        import user_manager

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(user_manager)

        user_manager.save_user(123456, "token_user", "abcdefghijklmnopqrstuvwxyz123456")
        row = user_manager.get_user(123456)
        stored_value = str(row[2] or "")
        _assert(stored_value.startswith("enc:v1:"), "stored token should be encrypted")
        _assert(stored_value != "abcdefghijklmnopqrstuvwxyz123456", "stored token must not remain plaintext")
        _assert(user_manager.get_user_token(123456) == "abcdefghijklmnopqrstuvwxyz123456", "token should decrypt on read")

        conn = sqlite3.connect(config.DB_NAME)
        try:
            db_value = conn.execute("SELECT wb_token FROM users WHERE telegram_id=123456").fetchone()[0]
        finally:
            conn.close()
        _assert(str(db_value).startswith("enc:v1:"), "database row should contain encrypted token")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("WB TOKEN STORAGE OK", flush=True)
