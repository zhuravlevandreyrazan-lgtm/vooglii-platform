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


def test_business_finance_system_show_customer_advertising_status(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda *args, **kwargs: {
            "business_health": "WARNING",
            "business_state": {"sales": "GOOD", "finance": "BLOCKED", "ads": "GOOD"},
            "main_recommendation": "Не закрывать месяц, пока WB не подтвердит финансовые данные.",
            "main_recommendation_action": "Проверить финансовые данные WB.",
            "risks": ["Финансовые данные WB ещё не подтверждены"],
            "today_actions": ["Открыть /advisor"],
            "advertising": {
                "total_spend": 29900.0,
                "normalized_status": "ADS_PARTIAL",
                "status_kind": "error",
            },
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_finance_center_snapshot",
        lambda *args, **kwargs: {
            "official_new_finance_available": False,
            "sales_for_pay_total": 5163.69,
            "payment_received_total": 0.0,
            "advertising_total": 29900.63,
            "official_net_profit": None,
            "coverage_percent": 100.0,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_system_center_snapshot",
        lambda *args, **kwargs: {
            "agent_status": "OK",
            "database_status": "OK",
            "sales_status": "OK",
            "finance_status": "WARNING",
            "ads_status": "OK",
            "wb_connected": True,
            "last_updates": {"sales": "2026-07-03 14:35:00"},
            "advertising": {
                "normalized_status": "ADS_PARTIAL",
                "total_spend": 29900.0,
                "campaigns_total": 10,
                "campaigns_linked": 8,
            },
        },
    )

    business = _Update("/business")
    _run(telegram_bot.business_command(business, _Context()))
    business_text = business.message.replies[-1]
    assert "29 900" in business_text
    assert "Реклама:" in business_text

    finance = _Update("/finance")
    _run(telegram_bot.finance_command(finance, _Context()))
    finance_text = finance.message.replies[-1]
    assert "Реклама WB: 29 900.63" in finance_text
    assert "Остальные расходы: ожидают подтверждения" in finance_text

    system = _Update("/system")
    _run(telegram_bot.system_command(system, _Context()))
    system_text = system.message.replies[-1]
    assert "Реклама: частично обновлена" in system_text
    assert "10 кампаний" in system_text
