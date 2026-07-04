from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


class _Message:
    def __init__(self, text: str):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _User:
    def __init__(self, user_id: int = 100, username: str = "owner_user"):
        self.id = user_id
        self.username = username


class _Update:
    def __init__(self, text: str):
        self.effective_user = _User()
        self.message = _Message(text)


class _Context:
    def __init__(self, args=None):
        self.args = list(args or [])


def _run(coro):
    return asyncio.run(coro)


def test_adsaudit_debug_is_engineering_only(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user_token", lambda _user_id: "token")
    monkeypatch.setattr(
        telegram_bot,
        "audit_advertising_period",
        lambda *_args, **_kwargs: {
            "period_begin": "2026-07-01",
            "period_end": "2026-07-31",
            "count_status": "SUCCESS",
            "fullstats_status": "SUCCESS",
            "campaigns_found": 10,
            "campaigns_loaded": 8,
            "campaigns_in_local": 8,
            "api_total_spend": 29900.63,
            "local_total_spend": 29900.51,
            "local_expenses_total": 29900.51,
            "campaigns": [],
            "api_daily": [],
            "local_daily": [],
            "missing_from_fullstats": [{"advert_id": "11"}],
            "missing_in_local": [],
            "local_only": [],
            "notes": [],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {"linkability_percent": 83.6, "coverage_percent": 100.0},
    )

    monkeypatch.setattr(telegram_bot, "_is_engineering_role", lambda _user_id: False)
    customer_update = _Update("/adsaudit debug")
    _run(telegram_bot.adsaudit_command(customer_update, _Context(["debug", "month"])))
    assert "Эта диагностика доступна только администратору." in customer_update.message.replies[-1]

    monkeypatch.setattr(telegram_bot, "_is_engineering_role", lambda _user_id: True)
    debug_update = _Update("/adsaudit debug")
    _run(telegram_bot.adsaudit_command(debug_update, _Context(["debug", "month"])))
    debug_text = debug_update.message.replies[-1]
    assert "promotion/count" in debug_text
    assert "fullstats" in debug_text
