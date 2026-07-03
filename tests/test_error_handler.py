from pathlib import Path
import asyncio
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    replies = []

    class _Message:
        text = "/dashboard"

        async def reply_text(self, text, **kwargs):
            replies.append(str(text))

    class _User:
        id = 999
        username = "error_user"

    class _Update:
        effective_user = _User()
        message = _Message()

    class _Context:
        error = RuntimeError("simulated failure")

    asyncio.run(telegram_bot.error_handler(_Update(), _Context()))
    _assert(any("Команда временно не выполнилась" in reply for reply in replies), "user should receive safe error text")


def test_main():
    main()


if __name__ == "__main__":
    main()
    print("ERROR HANDLER OK", flush=True)
