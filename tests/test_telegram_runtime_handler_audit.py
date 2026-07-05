from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_CUSTOMER_TOKENS = [
    "promotion/count",
    "fullstats",
    "FULLSTATS",
    "local advertising",
    "expense_rows",
    "rows",
    "campaign_ids",
    "ADS_PARTIAL_MISSING_IDS",
    "ADS_COOLDOWN",
    "UNKNOWN",
    "NOT_ACTIVE",
    "delta",
    "Product readiness",
    "UI Spec",
    "Release Candidate",
    "Structure readiness",
    "Performance",
    "/control center",
    "/rc status",
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


def _assert_clean(text: str):
    for token in FORBIDDEN_CUSTOMER_TOKENS:
        assert token not in text, f"forbidden token leaked into runtime output: {token}"


def test_registered_runtime_handlers_are_customer_safe(monkeypatch):
    outputs: dict[str, str] = {}

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs[update.message.text.split()[0]] = str(text)
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda user_id: "owner")
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: False)
    monkeypatch.setattr(telegram_bot, "get_user_token", lambda _user_id: "token")
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_PARTIAL",
            "status_kind": "error",
            "raw_status": "ADS_PARTIAL",
            "last_success": "2026-07-01 10:00:00",
            "total_spend": 29900.63,
            "linked_spend": 26000.00,
            "unlinked_spend": 3900.63,
            "linkability_percent": 86.9,
            "campaigns_total": 10,
            "campaigns_linked": 8,
            "campaigns_unlinked": 2,
            "status": "MEDIUM",
            "drr": 12.4,
            "roas": 3.21,
            "cpc": 15.2,
            "ctr": 1.9,
            "cpa": 210.4,
            "coverage_percent": 100.0,
            "delta": 1663.27,
        },
    )
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
            "api_total_spend": 31563.90,
            "local_total_spend": 29900.63,
            "local_expenses_total": 29900.63,
            "campaigns": [],
            "api_daily": [{"date": "2026-07-01", "spend": 1000.0}],
            "local_daily": [{"date": "2026-07-01", "spend": 900.0}],
            "missing_from_fullstats": [{"advert_id": "11"}, {"advert_id": "12"}],
            "missing_in_local": [],
            "local_only": [],
            "notes": [],
        },
    )
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
                "total_spend": 29900.63,
                "normalized_status": "ADS_PARTIAL",
                "status_kind": "error",
                "delta": 1663.27,
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
                "total_spend": 29900.63,
                "campaigns_total": 10,
                "campaigns_linked": 8,
                "delta": 1663.27,
            },
        },
    )

    handlers = telegram_bot._command_handlers()
    expected_modules = {
        "adsaudit": "vooglii_telegram.handlers.advertising",
        "business": "vooglii_telegram.handlers.business",
        "finance": "vooglii_telegram.handlers.finance",
        "system": "vooglii_telegram.handlers.system",
    }
    for command_name, expected_module in expected_modules.items():
        assert handlers[command_name].__module__ == expected_module

    runs = [
        ("adsaudit", _Update("/adsaudit"), _Context(["month"])),
        ("business", _Update("/business"), _Context()),
        ("finance", _Update("/finance"), _Context()),
        ("system", _Update("/system"), _Context()),
    ]
    for command_name, update, context in runs:
        _run(handlers[command_name](update, context))

    for key in ("/adsaudit", "/business", "/finance", "/system"):
        assert key in outputs
        _assert_clean(outputs[key])

    assert "Рекламный аудит" in outputs["/adsaudit"]
    assert "Расходы:" in outputs["/adsaudit"]
    assert "Расхождение с WB:" in outputs["/adsaudit"]
    assert "Реклама: 🟡 29 900.63" in outputs["/business"]
    assert "Реклама WB: 29 900.63" in outputs["/finance"]
    assert "Реклама: частично обновлена" in outputs["/system"]
    assert "10 кампаний" in outputs["/system"]


def test_registered_admin_handler_blocks_customer_before_legacy(monkeypatch):
    admin_entry_calls: list[str] = []
    handlers = telegram_bot._command_handlers()

    monkeypatch.setattr(telegram_bot, "admin", lambda _update: False)
    monkeypatch.setattr(telegram_bot, "developer", lambda _update: False)

    async def _unexpected_admin_entry(update, context):
        admin_entry_calls.append("called")
        await update.message.reply_text("/admin users\n/admin pro ID\n/admin role ID")

    monkeypatch.setattr(telegram_bot, "_admin_command_entry", _unexpected_admin_entry)

    assert handlers["admin"].__module__ == "vooglii_telegram.handlers.admin"

    update = _Update("/admin")
    _run(handlers["admin"](update, _Context()))
    text = update.message.replies[-1]

    assert text == "⛔ Команда недоступна."
    assert not admin_entry_calls
    assert "/admin users" not in text
    assert "/admin pro" not in text
    assert "/admin role" not in text


def test_registered_stocks_handler_hides_technical_status_for_customer(monkeypatch):
    outputs: dict[str, str] = {}
    handlers = telegram_bot._command_handlers()

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs[update.message.text.split()[0]] = str(text)
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "admin", lambda _update: False)
    monkeypatch.setattr(telegram_bot, "get_stocks", lambda _user: [("SKU-1", 4, None, 1, 0, "Коледино")])
    monkeypatch.setattr(telegram_bot, "get_sync_status_map", lambda _user: {"stocks": {"last_status": "SUCCESS"}})
    monkeypatch.setattr(telegram_bot, "_stock_snapshot_date", lambda _user: "2026-07-05")

    assert handlers["stocks"].__module__ == "vooglii_telegram.handlers.stocks"

    update = _Update("/stocks")
    _run(handlers["stocks"](update, _Context()))
    text = outputs["/stocks"]

    assert "Технический статус" not in text
    assert "SUCCESS" not in text
