from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


class _Message:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _User:
    def __init__(self, user_id: int = 100, username: str = "owner_user"):
        self.id = user_id
        self.username = username


class _Update:
    def __init__(self, text: str = "", user_id: int = 100, username: str = "owner_user"):
        self.effective_user = _User(user_id, username)
        self.message = _Message(text)


class _Context:
    def __init__(self, args=None):
        self.args = list(args or [])
        self.bot = SimpleNamespace()


def _run(coro):
    return asyncio.run(coro)


def test_rc3_button_routing_uses_single_expected_handler(monkeypatch):
    calls: list[tuple[str, list[str]]] = []

    def _stub_factory(name):
        async def _handler(update, context):
            calls.append((name, list(context.args or [])))
            await update.message.reply_text(f"{name}:{'|'.join(context.args or [])}")
        return _handler

    monkeypatch.setattr(telegram_bot, "_customer_all_time_range", lambda _user_id: ("2026-01-01", "2026-07-31"))
    monkeypatch.setattr(telegram_bot, "business_command", _stub_factory("business"))
    monkeypatch.setattr(telegram_bot, "report_command", _stub_factory("report"))
    monkeypatch.setattr(telegram_bot, "ceo_command", _stub_factory("ceo"))
    monkeypatch.setattr(telegram_bot, "stocks_command", _stub_factory("stocks"))
    monkeypatch.setattr(telegram_bot, "pnl_command", _stub_factory("pnl"))
    monkeypatch.setattr(telegram_bot, "advert_command", _stub_factory("advert"))
    monkeypatch.setattr(telegram_bot, "advisor_command", _stub_factory("advisor"))
    monkeypatch.setattr(telegram_bot, "profile_command", _stub_factory("profile"))
    monkeypatch.setattr(telegram_bot, "update_command", _stub_factory("update"))
    monkeypatch.setattr(telegram_bot, "menu_command", _stub_factory("menu"))

    expected = {
        "📅 Сегодня": ("business", ["today"]),
        "📆 Неделя": ("business", ["week"]),
        "🗓 Месяц": ("business", ["month"]),
        "♾ Всё время": ("business", ["2026-01-01", "2026-07-31"]),
        "📊 Отчёт": ("report", ["current_month"]),
        "👑 CEO": ("ceo", ["current_month"]),
        "📦 Остатки": ("stocks", []),
        "💰 P&L": ("pnl", ["current_month"]),
        "📢 Реклама": ("advert", ["current_month"]),
        "🤖 AI-советы": ("advisor", []),
        "⚠ Проблемы": ("business", ["current_month"]),
        "👤 Кабинет": ("profile", []),
        "🔄 Обновить": ("update", []),
        "⚙ Меню": ("menu", []),
    }

    for button_text, expected_call in expected.items():
        calls.clear()
        update = _Update(button_text)
        _run(telegram_bot.buttons(update, _Context()))
        assert calls == [expected_call], (button_text, calls)
        assert len(update.message.replies) == 1, (button_text, update.message.replies)
