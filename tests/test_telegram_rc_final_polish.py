from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot
import vooglii_telegram.legacy_bot as legacy_bot


FORBIDDEN_CUSTOMER_TOKENS = [
    "Команда временно не выполнилась.",
    "SUCCESS",
    "FAILED",
    "UNKNOWN",
    "NOT_ACTIVE",
    "promotion/count",
    "fullstats",
    "campaign_ids",
    "rows",
    "expense_rows",
    "delta",
    "local advertising",
    "FULLSTATS",
    "ADS_PARTIAL",
    "ADS_COOLDOWN",
    "current_month",
    "previous_month",
    "last_30_days",
    "admin users",
    "admin role",
    "admin pro",
]


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
    def __init__(self, args=None, bot=None):
        self.args = list(args or [])
        self.bot = bot or SimpleNamespace()


def _run(coro):
    return asyncio.run(coro)


def _assert_clean(text: str):
    for token in FORBIDDEN_CUSTOMER_TOKENS:
        assert token not in text, f"forbidden customer token leaked: {token}"


def test_period_handlers_and_period_buttons_open_business_screen(monkeypatch):
    outputs: dict[str, str] = {}

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs[update.message.text] = str(text)
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "_customer_all_time_range", lambda _user_id: ("2026-01-01", "2026-07-31"))
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda user, days: {
            "business_health": "WARNING",
            "business_state": {"sales": "GOOD", "finance": "BLOCKED", "ads": "GOOD"},
            "main_recommendation": "Проверить продажи за период.",
            "main_recommendation_action": "Открыть /business и сверить ключевые показатели.",
            "risks": ["Финансовые данные WB ещё не подтверждены"],
            "today_actions": ["Открыть /advisor"],
            "advertising": {"total_spend": 2500.0, "normalized_status": "ADS_OK", "status_kind": "ok", "delta": 0.0},
            "products": {"cost_coverage_percent": 100.0},
        },
    )

    handlers = telegram_bot._command_handlers()
    for command_name in ("today", "week", "month"):
        update = _Update(f"/{command_name}")
        _run(handlers[command_name](update, _Context()))
        text = update.message.replies[-1]
        _assert_clean(text)
        assert "Бизнес" in text

    for button_text in ("📅 Сегодня", "📆 Неделя", "🗓 Месяц", "♾ Всё время"):
        update = _Update(button_text)
        _run(telegram_bot.buttons(update, _Context()))
        text = update.message.replies[-1]
        _assert_clean(text)
        assert "Бизнес" in text


def test_advisor_default_and_button_open_customer_advisor(monkeypatch):
    outputs: list[str] = []

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs.append(str(text))
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda _user_id: "owner")
    monkeypatch.setattr(
        telegram_bot,
        "_advisor_customer_text",
        lambda _user_id, days: f"🤖 AI-советы\nПериод: {days[0]} - {days[1]}",
    )
    monkeypatch.setattr(legacy_bot, "_advisor_customer_text", telegram_bot._advisor_customer_text)

    handlers = telegram_bot._command_handlers()
    advisor_update = _Update("/advisor")
    _run(handlers["advisor"](advisor_update, _Context()))
    assert advisor_update.message.replies[-1].startswith("🤖 AI-советы")
    _assert_clean(advisor_update.message.replies[-1])

    button_update = _Update("🤖 AI-советы")
    _run(telegram_bot.buttons(button_update, _Context()))
    assert button_update.message.replies[-1].startswith("🤖 AI-советы")
    _assert_clean(button_update.message.replies[-1])


def test_pnl_buy_ceo_stocks_and_admin_are_customer_safe(monkeypatch):
    outputs: dict[str, str] = {}

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs[update.message.text] = str(text)
        update.message.replies.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "PAYMENT_PROVIDER_TOKEN", "")
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user_id, _days: {
            "revenue": 120000.0,
            "cost_price": 45000.0,
            "advertising": 29900.63,
            "logistics": 6300.0,
            "storage": 1200.0,
            "other": 500.0,
            "management_profit_with_storage": 18100.0,
        },
    )
    monkeypatch.setattr(legacy_bot, "_report_mgmt_snapshot", telegram_bot._report_mgmt_snapshot)
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None: {
            "official_new_finance_available": False,
            "official_net_profit": None,
        },
    )
    monkeypatch.setattr(legacy_bot, "_financial_engine_snapshot", telegram_bot._financial_engine_snapshot)
    monkeypatch.setattr(telegram_bot, "get_profit_stats", lambda _days, _user: (100000.0, 15000.0, 70000.0, 45000.0, 3000.0, 29900.63, 500.0, 0.0, 78900.63, 0.0, 18100.0, 18.1, 4))
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (12, 0.0, 0, 0.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (10, 0.0))
    monkeypatch.setattr(telegram_bot, "get_advertising_stats", lambda _days, _user: (0, 0, 0, 0.0, 29900.63, 0.0, 0.0, 3.2, 12.4))
    monkeypatch.setattr(telegram_bot, "_finance_local_expenses_analysis", lambda _user, _days: {"acquiring": 0.0, "deduction": 0.0, "hidden_difference": 0.0})
    monkeypatch.setattr(telegram_bot, "get_top_product", lambda _user: ("SKU-1",))
    monkeypatch.setattr(telegram_bot, "get_growth", lambda _user: 12.5)
    monkeypatch.setattr(telegram_bot, "get_stocks", lambda _user: [("SKU-1", 4, None, 1, 0, "Коледино")])
    monkeypatch.setattr(telegram_bot, "_roi_text_and_cost_warnings", lambda _days, _user: ("18.1%", ""))
    monkeypatch.setattr(
        telegram_bot,
        "_tax_report_lines",
        lambda _days, _user: (
            {
                "profit_before_tax": 18100.0,
                "tax": 0.0,
                "profit_after_tax": 18100.0,
                "margin_after_tax": 18.1,
                "tax_notes": [],
            },
            "",
        ),
    )
    monkeypatch.setattr(telegram_bot, "get_revenue_forecast", lambda _user: 150000.0)
    monkeypatch.setattr(telegram_bot, "get_stock_forecast", lambda _user, _horizon, _window: [])
    monkeypatch.setattr(telegram_bot, "get_replenishment_plan", lambda _user: {"items": [], "total_budget": 0.0})
    monkeypatch.setattr(telegram_bot, "admin", lambda _update: False)
    monkeypatch.setattr(telegram_bot, "developer", lambda _update: False)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda _user_id: "owner")
    monkeypatch.setattr(telegram_bot, "get_sync_status_map", lambda _user: {"stocks": {"last_status": "SUCCESS"}})
    monkeypatch.setattr(telegram_bot, "_stock_snapshot_date", lambda _user: "2026-07-04")

    handlers = telegram_bot._command_handlers()

    pnl_update = _Update("/pnl")
    _run(handlers["pnl"](pnl_update, _Context(["current_month"])))
    pnl_text = pnl_update.message.replies[-1]
    _assert_clean(pnl_text)
    assert "P&L" in pnl_text
    assert "операционная оценка" in pnl_text

    buy_update = _Update("/buy")
    _run(handlers["buy"](buy_update, _Context()))
    buy_text = buy_update.message.replies[-1]
    _assert_clean(buy_text)
    assert "VOOGLII PRO" in buy_text
    assert "Скоро будет доступна в боте." in buy_text
    assert "напишите владельцу сервиса." in buy_text

    ceo_update = _Update("👑 CEO")
    _run(telegram_bot.buttons(ceo_update, _Context()))
    ceo_text = ceo_update.message.replies[-1]
    _assert_clean(ceo_text)
    assert "CEO Dashboard" in ceo_text
    assert "Главная сводка" not in ceo_text

    stocks_update = _Update("/stocks")
    _run(handlers["stocks"](stocks_update, _Context()))
    stocks_text = stocks_update.message.replies[-1]
    _assert_clean(stocks_text)
    assert "Технический статус" not in stocks_text

    admin_update = _Update("/admin")
    _run(handlers["admin"](admin_update, _Context()))
    assert admin_update.message.replies[-1] == "⛔ Команда недоступна."
