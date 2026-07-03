from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_CUSTOMER_TOKENS = [
    "Wildberries Agent",
    "current_month",
    "last_7_days",
    "last_30_days",
    "today",
    "week",
    "month",
    "UNKNOWN",
    "UNAVAILABLE",
    "NOT_ACTIVE",
    "Release Candidate",
    "UI Spec",
    "Product readiness",
    "Structure readiness",
    "Performance",
    "Official Financial Engine",
    "/control center",
    "/rc status",
    "/migration readiness",
]


class _Message:
    def __init__(self, text: str):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _User:
    def __init__(self, user_id: int = 100, username: str = "audit_user"):
        self.id = user_id
        self.username = username


class _Update:
    def __init__(self, text: str, user_id: int = 100, username: str = "audit_user"):
        self.effective_user = _User(user_id, username)
        self.message = _Message(text)


class _Context:
    def __init__(self, args=None):
        self.args = list(args or [])


def _run(coro):
    return asyncio.run(coro)


def _assert_clean(text: str):
    for token in FORBIDDEN_CUSTOMER_TOKENS:
        assert token not in text, f"forbidden token leaked into runtime handler output: {token}"


def test_registered_customer_handlers_render_new_ux(monkeypatch):
    outputs: dict[str, str] = {}

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs[(getattr(update.message, "text", "") or "").split()[0]] = str(text)

    monkeypatch.setattr(telegram_bot, "ensure_user", lambda *args, **kwargs: None)
    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: False)
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: (1, "audit_user", "wb-token", "PRO", None, None, None, "owner", None))
    monkeypatch.setattr(telegram_bot, "_customer_profile_text", lambda user_row, name, user_id: "👤 Ваш кабинет VOOGLII\n\nСтатус WB: подключён")
    monkeypatch.setattr(telegram_bot, "_home_snapshot", lambda user, days: {
        "period_label": "Июль 2026",
        "sales_status": "OK",
        "finance_status": "WARNING",
        "ads_status": "OK",
        "costs_status": "WARNING",
        "wb_connected": True,
        "last_updates": {"sales": "2026-07-03 14:35:00"},
    })
    monkeypatch.setattr(telegram_bot, "_business_center_snapshot", lambda user, days: {
        "business_health": "WARNING",
        "business_state": {"sales": "OK", "finance": "WARNING", "ads": "OK"},
        "main_recommendation": "Проверить прибыль по итогам периода",
        "main_recommendation_action": "Открыть /finance и проверить расхождения.",
        "risks": ["Прибыль ещё не подтверждена WB"],
        "today_actions": ["Проверить финансовую сводку", "Обновить данные"],
    })
    monkeypatch.setattr(telegram_bot, "_finance_center_snapshot", lambda user, days: {
        "official_new_finance_available": False,
        "sales_for_pay_total": 125000.0,
        "payment_received_total": 98000.0,
        "official_net_profit": None,
        "coverage_percent": 82.0,
    })
    monkeypatch.setattr(telegram_bot, "_products_center_snapshot", lambda user, days: {
        "cost_coverage_percent": 78.0,
        "known_skus": 11,
        "missing_skus": 3,
        "critical_stock_count": 2,
        "top_risks": ["SKU-1 — остаток уже закончился", "SKU-2 — хватит примерно на 3 дн."],
        "stock_snapshot_date": "2026-07-03",
    })
    monkeypatch.setattr(telegram_bot, "_analytics_center_snapshot", lambda user, days: {
        "sales_available": "OK",
        "ads_available": "WARNING",
    })
    monkeypatch.setattr(telegram_bot, "_system_center_snapshot", lambda user, days: {
        "agent_status": "OK",
        "database_status": "OK",
        "sales_status": "OK",
        "finance_status": "WARNING",
        "ads_status": "OK",
        "wb_connected": True,
        "last_updates": {"sales": "2026-07-03 14:35:00"},
        "product_readiness": "WARNING",
        "structure_status": "READY",
        "known_blockers": [],
        "engineering_commands": [],
    })
    monkeypatch.setattr(telegram_bot, "_advisor_v2_text", lambda user, days, context=None: "🤖 Советник VOOGLII\n\nСегодня рекомендую:\n1. Проверить прибыль\n2. Обновить данные\n3. Посмотреть товары")

    handlers = telegram_bot._command_handlers()

    for command_name in ("start", "home", "business", "finance", "products", "analytics", "system", "advisor", "profile"):
        update = _Update(f"/{command_name}")
        _run(handlers[command_name](update, _Context()))
        if update.message.replies:
            outputs[f"/{command_name}"] = update.message.replies[-1]

    for command_name in ("/home", "/business", "/finance", "/products", "/analytics", "/system", "/advisor", "/profile"):
        assert command_name in outputs, f"expected runtime output for {command_name}"
        _assert_clean(outputs[command_name])

    assert outputs["/start"].startswith("🏢 VOOGLII Terminal")
    assert "Главная сводка" in outputs["/home"]
    assert "Что сделать сейчас" in outputs["/home"]
    assert "Проверить прибыль по итогам периода" in outputs["/business"]
    assert "WB ещё не предоставил официальные финансовые данные" in outputs["/finance"]
    assert "Основные проблемы" in outputs["/products"]
    assert "⚙ Состояние VOOGLII" in outputs["/system"]
    assert "Сегодня рекомендую" in outputs["/advisor"]
    assert "Ваш кабинет VOOGLII" in outputs["/profile"]
