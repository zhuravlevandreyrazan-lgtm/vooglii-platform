"""Readonly audit checks for Telegram bot identity configuration and branding."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    original_bot_token = telegram_bot.BOT_TOKEN
    original_bot_username = telegram_bot.BOT_USERNAME
    original_env_token = telegram_bot.os.environ.get("BOT_TOKEN")
    original_env_username = telegram_bot.os.environ.get("BOT_USERNAME")
    telegram_bot.os.environ["BOT_TOKEN"] = "123456789:TEST_TOKEN_EXAMPLE_ABCDEF"
    telegram_bot.os.environ["BOT_USERNAME"] = "vooglii_bot"
    telegram_bot.BOT_TOKEN = telegram_bot.os.environ["BOT_TOKEN"]
    telegram_bot.BOT_USERNAME = telegram_bot.os.environ["BOT_USERNAME"]
    try:
        identity_snapshot = telegram_bot._telegram_identity_snapshot()
        _assert(isinstance(identity_snapshot, dict), "telegram identity snapshot should be dict")
        _assert(str(identity_snapshot.get("brand") or "") == "VOOGLII", "telegram identity brand should be VOOGLII")
        _assert(str(identity_snapshot.get("config_source") or "") == "environment variable BOT_TOKEN", "telegram identity should use BOT_TOKEN from environment")
        _assert(str(identity_snapshot.get("bot_username_source") or "") == "environment variable BOT_USERNAME", "telegram identity should use BOT_USERNAME from environment")
        active_refs = list(identity_snapshot.get("active_references") or [])
        forbidden = ("wildberries_andrey_ai_bot", "Wildberries AI Agent")
        for item in active_refs:
            line = str(item.get("text") or "")
            _assert(not any(text in line for text in forbidden), "active references should not contain old bot identity")

        outputs, replies = _run_handler(telegram_bot.telegram_command, "/telegram identity", ["identity"])
        _assert(not replies, "telegram identity should not fall back to reply_text help")
        _assert(len(outputs) == 1, "telegram identity should render one output")
        text = outputs[0]
        _assert("TELEGRAM IDENTITY" in text, "telegram identity title missing")
        _assert("VOOGLII" in text, "telegram identity should contain VOOGLII")
        _assert("Old bot references: none" in text, "telegram identity should report no active old bot references")
        _assert("123456789:TEST_TOKEN_EXAMPLE_ABCDEF" not in text, "telegram identity must not contain full bot token")
        _assert("Token source: environment variable BOT_TOKEN" in text, "telegram identity should show environment BOT_TOKEN source")
        _assert("Username source: environment variable BOT_USERNAME" in text, "telegram identity should show environment BOT_USERNAME source")

        help_outputs, help_replies = _run_handler(telegram_bot.menu_command, "/help", [])
        _assert(not help_outputs and len(help_replies) == 1, "help should render one reply_text")
        _assert("VOOGLII" in help_replies[0], "help should contain VOOGLII")
        _assert("Wildberries AI Agent" not in help_replies[0], "help should not contain old brand")

        home_outputs, home_replies = _run_handler(telegram_bot.home_command, "/home", [])
        _assert(not home_replies and len(home_outputs) == 1, "home should render one output")
        _assert("VOOGLII" in home_outputs[0], "home should contain VOOGLII")
        _assert("Wildberries AI Agent" not in home_outputs[0], "home should not contain old brand")
    finally:
        telegram_bot.BOT_TOKEN = original_bot_token
        telegram_bot.BOT_USERNAME = original_bot_username
        if original_env_token is None:
            telegram_bot.os.environ.pop("BOT_TOKEN", None)
        else:
            telegram_bot.os.environ["BOT_TOKEN"] = original_env_token
        if original_env_username is None:
            telegram_bot.os.environ.pop("BOT_USERNAME", None)
        else:
            telegram_bot.os.environ["BOT_USERNAME"] = original_env_username


if __name__ == "__main__":
    main()
    print("TELEGRAM IDENTITY OK", flush=True)
