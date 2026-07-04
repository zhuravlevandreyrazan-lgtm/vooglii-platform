from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_TOKENS = [
    "promotion/count",
    "fullstats",
    "FULLSTATS",
    "campaign_ids",
    "local advertising",
    "expense_rows",
    "ADS_PARTIAL_MISSING_IDS",
    "ADS_COOLDOWN",
    "UNKNOWN",
    "NOT_ACTIVE",
    "delta",
]


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


def _assert_clean(text: str):
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden token leaked: {token}"


def test_advert_and_adsaudit_customer_outputs_are_clean(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user_token", lambda _user_id: "token")
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_PARTIAL",
            "status_kind": "error",
            "raw_status": "ADS_PARTIAL",
            "last_success": "2026-07-04 12:00:00",
            "total_spend": 29900.63,
            "linked_spend": 25000.00,
            "unlinked_spend": 4900.63,
            "linkability_percent": 83.6,
            "campaigns_total": 8,
            "campaigns_linked": 6,
            "campaigns_unlinked": 2,
            "status": "MEDIUM",
            "drr": 12.4,
            "roas": 3.21,
            "cpc": 15.2,
            "ctr": 1.9,
            "cpa": 210.4,
            "coverage_percent": 100.0,
            "delta": 0.12,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "audit_advertising_period",
        lambda *_args, **_kwargs: {
            "period_begin": "2026-07-01",
            "period_end": "2026-07-31",
            "api_total_spend": 29900.63,
            "local_total_spend": 29900.51,
            "campaigns_found": 10,
            "campaigns_loaded": 8,
            "missing_from_fullstats": [{"advert_id": "11"}, {"advert_id": "12"}],
            "api_daily": [{"date": "2026-07-01", "spend": 1000.0}],
        },
    )

    advert_update = _Update("/advert")
    _run(telegram_bot.advert_command(advert_update, _Context()))
    advert_text = advert_update.message.replies[-1]
    _assert_clean(advert_text)
    assert "📢 Реклама WB" in advert_text
    assert "Что важно:" in advert_text
    assert "Что сделать:" in advert_text

    adsaudit_update = _Update("/adsaudit")
    _run(telegram_bot.adsaudit_command(adsaudit_update, _Context(["month"])))
    adsaudit_text = adsaudit_update.message.replies[-1]
    _assert_clean(adsaudit_text)
    assert "📢 Рекламный аудит" in adsaudit_text
    assert "Реклама требует проверки" in adsaudit_text
    assert "WB не вернул статистику" in adsaudit_text
