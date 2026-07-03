from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


FORBIDDEN_CUSTOMER_TOKENS = [
    "Wildberries Agent",
    "/help developer",
    "current_month",
    "previous_month",
    "last_7_days",
    "last_30_days",
    "Legacy fallback",
    "UNKNOWN",
    "UNAVAILABLE",
    "NOT_ACTIVE",
    "Release Candidate",
    "UI Spec",
    "Product readiness",
    "Structure readiness",
    "Performance",
    "Official Financial Engine",
    "local/dev",
    "local SQLite",
    "PostgreSQL",
    "owner only",
    "????",
    "/director",
    "/cfo",
    "/kpi",
    "/decision",
    "/control center",
    "/rc status",
    "/migration readiness",
]

FORBIDDEN_TECHNICAL_COMMANDS = [
    "/admin",
    "/health",
    "/syncstatus",
    "/apistatus",
    "/control",
    "/migration",
    "/performance",
    "/structure",
    "/telegram",
    "/ui",
    "/rc",
    "/data",
    "/adsfullstatsprobe",
]


class _Message:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _User:
    def __init__(self, user_id: int = 100, username: str = "demo_user"):
        self.id = user_id
        self.username = username


class _Update:
    def __init__(self, text: str = "", user_id: int = 100, username: str = "demo_user"):
        self.effective_user = _User(user_id, username)
        self.message = _Message(text)


class _Context:
    def __init__(self, args=None, application=None):
        self.args = list(args or [])
        self.application = application


def _run(coro):
    return asyncio.run(coro)


def _assert_clean(text: str):
    for token in FORBIDDEN_CUSTOMER_TOKENS:
        assert token not in text, f"forbidden customer token found: {token}"


def _allow_access(*_args, **_kwargs):
    async def _inner(*args, **kwargs):
        return True
    return _inner


def test_start_menu_and_help_handlers_use_ux_v2(monkeypatch):
    monkeypatch.setattr(telegram_bot, "ensure_user", lambda *args, **kwargs: None)

    start_update = _Update("/start")
    menu_update = _Update("/menu")

    _run(telegram_bot.start_command(start_update, _Context()))
    _run(telegram_bot.menu_command(menu_update, _Context()))

    start_text = start_update.message.replies[-1]
    menu_text = menu_update.message.replies[-1]

    _assert_clean(start_text)
    _assert_clean(menu_text)
    assert "VOOGLII Terminal" in start_text
    assert "Главное меню" in menu_text
    assert "Сегодня" not in menu_text


def test_profile_and_account_handlers_use_customer_screen(monkeypatch):
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: (1, "demo_user", "", "FREE", None, None, None, "owner", None))
    monkeypatch.setattr(telegram_bot, "format_tax_settings_label", lambda _user_id: "не настроен")

    account_outputs: list[str] = []

    async def _capture_send_long(update, text, **kwargs):
        account_outputs.append(str(text))

    monkeypatch.setattr(telegram_bot, "send_long", _capture_send_long)

    profile_update = _Update("/profile")
    account_update = _Update("/account")

    _run(telegram_bot.profile_command(profile_update, _Context()))
    _run(telegram_bot.account_command(account_update, _Context()))

    profile_text = profile_update.message.replies[-1]
    account_text = account_outputs[-1]

    _assert_clean(profile_text)
    _assert_clean(account_text)
    assert "Ваш кабинет VOOGLII" in profile_text
    assert "Ваш кабинет VOOGLII" in account_text


def test_customer_dashboard_handlers_are_clean(monkeypatch):
    outputs: list[str] = []

    async def _capture_send_long(update, text, **kwargs):
        outputs.append(str(text))

    async def _access(*args, **kwargs):
        return True

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "send_long", _capture_send_long)
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: False)
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: None)
    monkeypatch.setattr(telegram_bot, "_home_snapshot", lambda user, days: {
        "period_label": "Июль 2026",
        "sales_status": "WARNING",
        "finance_status": "WARNING",
        "ads_status": "WARNING",
        "costs_status": "OK",
    })
    monkeypatch.setattr(telegram_bot, "_business_center_snapshot", lambda user, days: {
        "business_health": "WARNING",
        "business_state": {"sales": "WARNING", "finance": "WARNING", "ads": "WARNING", "data_quality": "OK"},
    })
    monkeypatch.setattr(telegram_bot, "_finance_center_snapshot", lambda user, days: {
        "official_new_finance_available": False,
        "sales_for_pay_total": 0,
        "payment_received_total": 0,
        "official_net_profit": None,
    })
    monkeypatch.setattr(telegram_bot, "_products_center_snapshot", lambda user, days: {
        "cost_coverage_percent": 100.0,
        "known_skus": 14,
        "missing_skus": 0,
        "critical_stock_count": 0,
        "stock_snapshot_date": None,
    })
    monkeypatch.setattr(telegram_bot, "_analytics_center_snapshot", lambda user, days: {
        "sales_available": "WARNING",
        "ads_available": "WARNING",
    })
    monkeypatch.setattr(telegram_bot, "_system_center_snapshot", lambda user, days: {
        "agent_status": "OK",
        "product_readiness": "WARNING",
        "structure_status": "READY",
        "known_blockers": [],
        "engineering_commands": [],
    })

    update = _Update("/home")
    _run(telegram_bot.home_command(update, _Context()))
    _run(telegram_bot.business_command(update, _Context()))
    _run(telegram_bot.finance_command(update, _Context()))
    _run(telegram_bot.products_command(update, _Context()))
    _run(telegram_bot.analytics_command(update, _Context()))
    _run(telegram_bot.system_command(update, _Context()))

    assert outputs, "expected captured customer dashboard outputs"
    for text in outputs:
        _assert_clean(text)


def test_connect_update_and_stocks_handlers_use_customer_empty_states(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    stocks_outputs: list[str] = []

    async def _capture_send_long(update, text, **kwargs):
        stocks_outputs.append(str(text))

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "get_user_token", lambda _user_id: "")
    monkeypatch.setattr(telegram_bot, "get_stocks", lambda _user_id: [])
    monkeypatch.setattr(telegram_bot, "get_sync_status_map", lambda _user_id: {"stocks": {}})
    monkeypatch.setattr(telegram_bot, "_stock_snapshot_date", lambda _user_id: None)
    monkeypatch.setattr(telegram_bot, "send_long", _capture_send_long)
    monkeypatch.setattr(telegram_bot, "admin", lambda _update: False)

    connect_update = _Update("/connect")
    update_update = _Update("/update")
    stocks_update = _Update("/stocks")

    _run(telegram_bot.connect_command(connect_update, _Context()))
    _run(telegram_bot.update_command(update_update, _Context()))
    _run(telegram_bot.stocks_command(stocks_update, _Context()))

    connect_text = connect_update.message.replies[-1]
    update_text = update_update.message.replies[-1]
    stocks_text = stocks_outputs[-1]

    _assert_clean(connect_text)
    _assert_clean(update_text)
    _assert_clean(stocks_text)
    assert "/connect ВАШ_API_КЛЮЧ" in connect_text
    assert "Кабинет WB не подключён" in update_text
    assert "Данные по остаткам пока не загружены." in stocks_text


def test_adsupdate_partial_status_is_customer_safe(monkeypatch):
    async def _access(*args, **kwargs):
        return True

    monkeypatch.setattr(telegram_bot, "access", _access)
    monkeypatch.setattr(telegram_bot, "get_user_token", lambda _user_id: "token")
    monkeypatch.setattr(telegram_bot, "get_api_cooldown", lambda _user_id, _block: None)
    monkeypatch.setattr(
        telegram_bot,
        "load_ads_for_user",
        lambda _user_id, _token, _days: (
            0,
            {
                "blocks": {
                    "advertising": {
                        "status": "ADS_PARTIAL_MISSING_IDS:demo",
                        "details": {
                            "campaigns_sent": 5,
                            "advert_ids_received": 3,
                            "advert_ids_missing": 2,
                            "missing_advert_ids": [111, 222],
                        },
                    }
                }
            },
        ),
    )

    update = _Update("/adsupdate")
    _run(telegram_bot.adsupdate_command(update, _Context()))

    text = update.message.replies[-1]
    _assert_clean(text)
    assert "Рекламные данные обновлены частично" in text
    assert "Часть кампаний пока не удалось связать с товарами WB" in text
    assert "ADS_PARTIAL_MISSING_IDS" not in text
    assert "missing ids" not in text


def test_customer_menu_help_and_system_hide_technical_commands(monkeypatch):
    outputs: list[str] = []

    async def _send_long(update, text, **kwargs):
        outputs.append(str(text))

    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: False)
    monkeypatch.setattr(telegram_bot, "get_user_role", lambda user_id: "owner")
    monkeypatch.setattr(
        telegram_bot,
        "_system_center_snapshot",
        lambda user, days: {
            "agent_status": "OK",
            "database_status": "OK",
            "sales_status": "OK",
            "finance_status": "OK",
            "ads_status": "OK",
            "wb_connected": True,
            "last_updates": {},
            "product_readiness": "WARNING",
            "structure_status": "READY",
            "known_blockers": [],
            "engineering_commands": [
                "/control center",
                "/performance",
                "/rc status",
                "/migration readiness",
                "/structure readiness",
            ],
        },
    )

    menu_update = _Update("/menu")
    help_update = _Update("/help")
    system_update = _Update("/system")

    _run(telegram_bot.menu_command(menu_update, _Context()))
    _run(telegram_bot.menu_command(help_update, _Context()))
    _run(telegram_bot.system_command(system_update, _Context()))

    texts = [menu_update.message.replies[-1], help_update.message.replies[-1], outputs[-1]]
    for text in texts:
        for command in FORBIDDEN_TECHNICAL_COMMANDS:
            assert command not in text, f"technical command leaked into customer surface: {command}"


def test_customer_paywall_is_clean(monkeypatch):
    replies: list[str] = []

    async def _reply_text(text, **kwargs):
        replies.append(str(text))

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=100, username="demo_user"),
        message=SimpleNamespace(reply_text=_reply_text),
    )
    permission_result = SimpleNamespace(allowed=True, role="viewer", permission="report")

    monkeypatch.setattr(telegram_bot, "require_permission", lambda user_id, permission: permission_result)
    monkeypatch.setattr(telegram_bot, "user_has_access", lambda user_id, feature: False)

    allowed = _run(telegram_bot.access(update, "report"))

    assert allowed is False
    assert replies
    _assert_clean(replies[-1])
    assert "VOOGLII PRO" in replies[-1]
