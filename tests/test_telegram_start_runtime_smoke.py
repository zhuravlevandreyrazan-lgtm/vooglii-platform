from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_START_TOKENS = [
    "Wildberries Agent",
    "today",
    "week",
    "month",
    "current_month",
    "last_7_days",
    "last_30_days",
]


class _Message:
    def __init__(self, text: str = "/start"):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _User:
    id = 4242
    username = "runtime_smoke"


class _Update:
    effective_user = _User()
    message = _Message()


class _Context:
    args = []


def test_registered_start_handler_uses_new_runtime_screen(monkeypatch):
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda *args, **kwargs: None)

    handlers = telegram_bot._command_handlers()
    assert handlers["start"] is telegram_bot.start_command

    update = _Update()
    context = _Context()
    asyncio.run(handlers["start"](update, context))

    assert update.message.replies, "start handler should reply"
    text = update.message.replies[-1]
    assert text.startswith("🏢 VOOGLII Terminal")
    for token in FORBIDDEN_START_TOKENS:
        assert token not in text, f"forbidden token leaked into /start runtime output: {token}"
