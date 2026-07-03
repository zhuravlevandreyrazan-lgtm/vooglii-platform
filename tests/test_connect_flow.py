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

        replies = []

        class _Message:
            text = "/connect abcdefghijklmnopqrstuvwxyz123456"

            async def reply_text(self, text, **kwargs):
                replies.append(str(text))

        class _User:
            id = 777
            username = "connect_user"

        class _Update:
            effective_user = _User()
            message = _Message()

        class _Context:
            args = ["abcdefghijklmnopqrstuvwxyz123456"]
            application = None

        asyncio.run(telegram_bot.connect_command(_Update(), _Context()))
        token = user_manager.get_user_token(777)
        row = user_manager.get_user(777)

        _assert(token == "abcdefghijklmnopqrstuvwxyz123456", "connect flow should save token")
        _assert(str(row[2] or "").startswith("enc:v1:"), "connect flow should persist encrypted token")
        _assert(all("abcdefghijklmnopqrstuvwxyz123456" not in reply for reply in replies), "connect reply must not echo token")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("CONNECT FLOW OK", flush=True)
