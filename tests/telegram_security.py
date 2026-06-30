"""Readonly security checks for Telegram environment-only configuration."""

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
import telegram_bot


TEST_USER_ID = 658486226


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _run_handler(handler, command_text, args):
    outputs = []
    replies = []
    original_send_long = telegram_bot.send_long
    original_access = telegram_bot.access
    original_user_has_access = telegram_bot.user_has_access

    class _Message:
        def __init__(self, text):
            self.text = text

        async def reply_text(self, text, **kwargs):
            replies.append(str(text))

    class _User:
        id = TEST_USER_ID
        username = "readonly_user"

    class _Update:
        def __init__(self, text):
            self.message = _Message(text)
            self.effective_user = _User()

    class _Context:
        def __init__(self, args):
            self.args = list(args)
            self.application = None

    async def _fake_send_long(update, text):
        outputs.append(str(text))

    async def _fake_access(update, permission):
        return True

    async def _invoke():
        telegram_bot.send_long = _fake_send_long
        telegram_bot.access = _fake_access
        telegram_bot.user_has_access = lambda user_id, permission=None: True
        try:
            await handler(_Update(command_text), _Context(args))
        finally:
            telegram_bot.send_long = original_send_long
            telegram_bot.access = original_access
            telegram_bot.user_has_access = original_user_has_access

    telegram_bot.asyncio.run(_invoke())
    return outputs, replies


def main():
    config_text = Path("config.py").read_text(encoding="utf-8")
    _assert("your_telegram_bot_token" not in config_text, "config.py should not contain placeholder token values")
    _assert("BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()" in config_text, "BOT_TOKEN should be read from environment without fallback")
    _assert("BOT_USERNAME = os.getenv('BOT_USERNAME', 'unknown').strip() or 'unknown'" in config_text, "BOT_USERNAME should be read from environment")

    original_bot_token = os.environ.get("BOT_TOKEN")
    original_bot_username = os.environ.get("BOT_USERNAME")
    original_config_bot_token = telegram_bot.BOT_TOKEN
    original_config_bot_username = telegram_bot.BOT_USERNAME
    try:
        os.environ["BOT_TOKEN"] = "123456789:TEST_TOKEN_EXAMPLE_ABCDEF"
        os.environ["BOT_USERNAME"] = "vooglii_bot"
        telegram_bot.BOT_TOKEN = os.environ["BOT_TOKEN"]
        telegram_bot.BOT_USERNAME = os.environ["BOT_USERNAME"]

        snapshot = telegram_bot._telegram_identity_snapshot()
        _assert(str(snapshot.get("config_source") or "") == "environment variable BOT_TOKEN", "token source should be environment variable BOT_TOKEN")
        _assert(str(snapshot.get("bot_username_source") or "") == "environment variable BOT_USERNAME", "username source should be environment variable BOT_USERNAME")
        _assert(str(snapshot.get("bot_username") or "") == "vooglii_bot", "bot username should come from environment")
        _assert(str(snapshot.get("token_masked") or "") == "********", "token should be masked")

        outputs, replies = _run_handler(telegram_bot.telegram_command, "/telegram identity", ["identity"])
        _assert(not replies and len(outputs) == 1, "telegram identity should render one output")
        text = outputs[0]
        _assert("123456789:TEST_TOKEN_EXAMPLE_ABCDEF" not in text, "telegram identity must not print full token")
        _assert("Token source: environment variable BOT_TOKEN" in text, "telegram identity should report environment BOT_TOKEN")
        _assert("Username source: environment variable BOT_USERNAME" in text, "telegram identity should report environment BOT_USERNAME")
    finally:
        if original_bot_token is None:
            os.environ.pop("BOT_TOKEN", None)
        else:
            os.environ["BOT_TOKEN"] = original_bot_token
        if original_bot_username is None:
            os.environ.pop("BOT_USERNAME", None)
        else:
            os.environ["BOT_USERNAME"] = original_bot_username
        telegram_bot.BOT_TOKEN = original_config_bot_token
        telegram_bot.BOT_USERNAME = original_config_bot_username

    _assert(config.BOT_USERNAME in ("unknown", os.getenv("BOT_USERNAME", "unknown")), "config BOT_USERNAME should remain environment-based")


if __name__ == "__main__":
    main()
    print("TELEGRAM SECURITY OK", flush=True)
