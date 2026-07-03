from __future__ import annotations

import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_SYSTEM_AND_BUSINESS_TOKENS = [
    "Product readiness",
    "UI Spec",
    "Release Candidate",
    "Structure readiness",
    "Performance",
    "/control center",
    "/rc status",
    "GOOD",
    "Finance API",
    "восстановления финансовые данные",
    "Дождаться финансовые данные",
    "данные ещё загружаются",
    "требует внимания",
    "требует проверки",
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


def _assert_forbidden_tokens_absent(text: str):
    for token in FORBIDDEN_SYSTEM_AND_BUSINESS_TOKENS:
        assert token not in text, f"forbidden token leaked into runtime output: {token}"


def test_runtime_system_and_business_handlers_are_customer_safe_for_owner(monkeypatch):
    outputs: dict[str, str] = {}

    async def _access(*args, **kwargs):
        return True

    async def _send_long(update, text, **kwargs):
        outputs[update.message.text.split()[0]] = str(text)

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: True)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda user_id: "owner")
    monkeypatch.setattr(telegram_bot, "_business_center_snapshot", lambda user, days: {
        "business_health": "WARNING",
        "business_state": {"sales": "GOOD", "finance": "BLOCKED", "ads": "GOOD"},
        "main_recommendation": "Дождаться Finance API перед закрытием месяца",
        "main_recommendation_action": "Проверить финансовые данные WB и не закрывать месяц раньше времени.",
        "risks": ["Финансовые данные зависят от Finance API"],
        "today_actions": ["Сверить финансовые данные WB", "Открыть /advisor"],
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
        "known_blockers": ["Finance API waits for confirmation"],
        "engineering_commands": ["/control center", "/rc status"],
    })

    handlers = telegram_bot._command_handlers()

    for command_name in ("system", "business"):
        update = _Update(f"/{command_name}")
        _run(handlers[command_name](update, _Context()))

    assert "/system" in outputs
    assert "/business" in outputs

    system_text = outputs["/system"]
    business_text = outputs["/business"]

    _assert_forbidden_tokens_absent(system_text)
    _assert_forbidden_tokens_absent(business_text)

    assert "⚙ Состояние VOOGLII" in system_text
    assert "Что можно сделать" in system_text
    assert "VOOGLII SYSTEM" not in system_text
    assert "Последнее обновление:" in system_text

    assert "📊 Бизнес" in business_text
    assert "🟢 Хорошо" in business_text
    assert "🟡 Ожидает данные WB" in business_text
    assert "финансовые данные WB" in business_text
    assert "нужно проверить" in business_text
    assert "Не закрывать месяц, пока WB не подтвердит финансовые данные." in business_text
