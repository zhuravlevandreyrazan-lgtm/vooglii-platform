from pathlib import Path
import importlib
import os
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
        import telegram_bot
        from vooglii_telegram.services import sync_service

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(telegram_bot)
        importlib.reload(sync_service)

        text = sync_service.format_sync_result(
            {
                "saved": 0,
                "status": {
                    "blocks": {
                        "sales": {"status": "SUCCESS"},
                        "orders": {"status": "SUCCESS"},
                        "stocks": {"status": "SUCCESS"},
                        "finance": {"status": "SUCCESS"},
                        "advertising": {"status": "ADS_PARTIAL_MISSING_IDS:sample"},
                    }
                },
            }
        )
        _assert("Рекламные данные обновлены частично" in text, "partial ads message should be customer-facing")
        _assert("Часть кампаний пока не удалось связать с товарами WB." in text, "partial ads explanation missing")
        _assert("ADS_PARTIAL_MISSING_IDS" not in text, "raw ads partial marker should not leak")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("UPDATE SYNC SERVICE OK", flush=True)
