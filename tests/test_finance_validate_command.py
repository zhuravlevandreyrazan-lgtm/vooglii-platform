from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vooglii_telegram.handlers.finance import finance_command


class _Message:
    def __init__(self):
        self.texts: list[str] = []

    async def reply_text(self, text):
        self.texts.append(text)


class _Bot:
    async def access(self, update, permission):
        return True

    def uid(self, _update):
        return 42

    async def _finance_command_entry(self, update, context):
        await update.message.reply_text("legacy finance route")


def test_finance_validate_command_shows_validation_mode(monkeypatch):
    monkeypatch.setattr("vooglii_telegram.handlers.finance.get_bot", lambda: _Bot())
    monkeypatch.setattr(
        "vooglii_telegram.handlers.finance.finance_validate_summary_text",
        lambda _user_id: (
            "Сверка с официальным отчётом WB\n\n"
            "Режим:\nСверка с официальным отчётом WB\n\n"
            "Показатели:\nВыручка WB: PASS\nК перечислению WB: PASS"
        ),
    )
    update = SimpleNamespace(message=_Message())
    context = SimpleNamespace(args=["validate"])

    asyncio.run(finance_command(update, context))

    assert update.message.texts
    text = update.message.texts[0]
    assert "Режим:" in text
    assert "Сверка с официальным отчётом WB" in text
    assert "К перечислению WB" in text
    assert "прибыль" not in text.lower()
