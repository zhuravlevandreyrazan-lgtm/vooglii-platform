from pathlib import Path
import importlib
import os
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["APP_ENV"] = "development"
        os.environ["DB_DIR"] = tmp_dir
        os.environ["BOT_TOKEN"] = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"

        import config
        import db_manager
        from scripts import check_telegram_bot_health

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(check_telegram_bot_health)

        check_telegram_bot_health.main()


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("TELEGRAM HEALTHCHECK OK", flush=True)
