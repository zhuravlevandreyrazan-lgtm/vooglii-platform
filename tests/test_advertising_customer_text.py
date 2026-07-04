from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_CUSTOMER_TOKENS = [
    "ADS_PARTIAL_MISSING_IDS",
    "fullstats",
    "campaign_ids",
    "UNKNOWN",
    "NOT_ACTIVE",
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
    def __init__(self, text: str, user_id: int = 100, username: str = "owner_user"):
        self.effective_user = _User(user_id, username)
        self.message = _Message(text)


class _Context:
    def __init__(self, args=None):
        self.args = list(args or [])


def _run(coro):
    return asyncio.run(coro)


def _assert_customer_safe(text: str):
    for token in FORBIDDEN_CUSTOMER_TOKENS:
        assert token not in text, f"forbidden advertising token leaked: {token}"


def test_adsupdate_and_advert_outputs_are_customer_safe(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "admin", lambda _update: False)
    monkeypatch.setattr(telegram_bot, "get_user_token", lambda _user_id: "token")
    monkeypatch.setattr(telegram_bot, "get_api_cooldown", lambda _user_id, _block: None)
    monkeypatch.setattr(
        telegram_bot,
        "load_ads_for_user",
        lambda _user_id, _token, _days: (
            2,
            {
                "blocks": {
                    "advertising": {
                        "status": "ADS_PARTIAL",
                        "details": {
                            "campaigns_sent": 5,
                            "period_begin": "2026-06-01",
                            "period_end": "2026-06-30",
                            "days_received": 20,
                            "spend_loaded": 1200.0,
                            "normalized_status": "ADS_PARTIAL",
                        },
                    }
                }
            },
        ),
    )
    monkeypatch.setattr(telegram_bot, "get_advertising_stats", lambda _days, _user: (1000, 100, 20, 15000.0, 1200.0, 10.0, 12.0, 12.5, 8.0))
    monkeypatch.setattr(
        telegram_bot,
        "get_sync_status_map",
        lambda _user: {"advertising": {"last_status": "ADS_PARTIAL", "last_success": "2026-07-01 10:00:00"}},
    )
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_PARTIAL",
            "status_kind": "error",
            "raw_status": "ADS_PARTIAL",
            "last_success": "2026-07-01 10:00:00",
            "total_spend": 1200.0,
            "linked_spend": 900.0,
            "unlinked_spend": 300.0,
            "linkability_percent": 75.0,
            "campaigns_total": 3,
            "campaigns_linked": 2,
            "campaigns_unlinked": 1,
            "status": "MEDIUM",
            "drr": 8.0,
            "roas": 12.5,
            "cpc": 12.0,
            "ctr": 10.0,
            "cpa": 60.0,
            "coverage_percent": 100.0,
            "delta": 0.0,
        },
    )

    adsupdate = _Update("/adsupdate")
    _run(telegram_bot.adsupdate_command(adsupdate, _Context()))
    update_text = adsupdate.message.replies[-1]
    _assert_customer_safe(update_text)
    assert "Рекламные данные обновлены частично" in update_text

    advert = _Update("/advert")
    _run(telegram_bot.advert_command(advert, _Context()))
    advert_text = advert.message.replies[-1]
    _assert_customer_safe(advert_text)
    assert "📢 Реклама WB" in advert_text
    assert "Расходы:" in advert_text
