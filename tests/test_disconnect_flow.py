from pathlib import Path
import asyncio
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
        import user_manager
        import telegram_bot

        importlib.reload(config)
        importlib.reload(db_manager)
        importlib.reload(user_manager)
        importlib.reload(telegram_bot)

        user_manager.save_user(778, "disconnect_user", "abcdefghijklmnopqrstuvwxyz123456")

        class _Message:
            text = "/disconnect"
            async def reply_text(self, text, **kwargs):
                pass

        class _User:
            id = 778
            username = "disconnect_user"

        class _Update:
            effective_user = _User()
            message = _Message()

        class _Context:
            args = []
            application = None

        asyncio.run(telegram_bot.disconnect_command(_Update(), _Context()))
        _assert(user_manager.get_user_token(778) is None, "disconnect should clear stored token")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("DISCONNECT FLOW OK", flush=True)
