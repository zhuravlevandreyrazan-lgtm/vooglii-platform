from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def test_customer_start_and_menu_are_commercial():
    start_text = telegram_bot._start_text()
    menu_text = telegram_bot._main_menu_text()

    assert "Wildberries Agent" not in start_text
    assert "Wildberries Agent" not in menu_text
    assert "/help developer" not in start_text
    assert "/help developer" not in menu_text
    assert "VOOGLII Terminal" in start_text
    assert "Главное меню" in menu_text
    assert "current_month" not in menu_text
    assert "last_30_days" not in start_text


def test_customer_profile_looks_like_product_screen(monkeypatch):
    monkeypatch.setattr(telegram_bot, "format_tax_settings_label", lambda _user_id: "не настроен")
    user_row = (1, "demo", "", "FREE", None, None, None, "owner", None)

    text = telegram_bot._customer_profile_text(user_row, "@demo", 1)

    assert "👤 Ваш кабинет VOOGLII" in text
    assert "Тариф: Free" in text
    assert "Роль: владелец" in text
    assert "Статус WB: не подключён" in text
    assert "FREE" not in text


def test_customer_system_hides_engineering_commands(monkeypatch):
    monkeypatch.setattr(
        telegram_bot,
        "_system_center_snapshot",
        lambda user, days: {
            "agent_status": "OK",
            "product_readiness": "WARNING",
            "structure_status": "READY",
            "known_blockers": ["Finance API waits for confirmation"],
            "engineering_commands": ["/control center", "/performance", "/rc status"],
        },
    )
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: False)
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: None)

    text = telegram_bot._system_center_text(1, ("2026-07-01", "2026-07-31"))

    assert "Состояние VOOGLII" in text
    assert "/control center" not in text
    assert "/performance" not in text
    assert "/rc status" not in text


def test_developer_system_keeps_engineering_commands(monkeypatch):
    monkeypatch.setattr(
        telegram_bot,
        "_system_center_snapshot",
        lambda user, days: {
            "agent_status": "OK",
            "product_readiness": "WARNING",
            "structure_status": "READY",
            "known_blockers": ["Finance API waits for confirmation"],
            "engineering_commands": ["/control center", "/performance", "/rc status"],
        },
    )
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: True)

    text = telegram_bot._system_center_text(1, ("2026-07-01", "2026-07-31"))

    assert "/control center" in text
    assert "/performance" in text
    assert "/rc status" in text


def test_pro_lock_is_value_based():
    text = telegram_bot._pro_upsell_text()

    assert "Доступно в VOOGLII PRO" in text
    assert "AI-советник" in text
    assert "/buy" in text
    assert "ошибка доступа" not in text.lower()


def test_customer_surfaces_have_no_mojibake(monkeypatch):
    monkeypatch.setattr(telegram_bot, "format_tax_settings_label", lambda _user_id: "не настроен")
    monkeypatch.setattr(
        telegram_bot,
        "_home_snapshot",
        lambda user, days: {
            "period_label": "Июль 2026",
            "sales_status": "OK",
            "finance_status": "WARNING",
            "ads_status": "OK",
            "costs_status": "WARNING",
            "sections": ["📊 Business", "💰 Finance", "📦 Products"],
            "director_command": "/director",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda user, days: {
            "period": "2026-07-01..2026-07-31",
            "business_health": "WARNING",
            "business_state": {"sales": "OK", "ads": "WARNING", "data_quality": "OK", "finance": "WARNING"},
            "risks": ["Требуется дождаться официальных финансовых данных."],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_finance_center_snapshot",
        lambda user, days: {
            "period": "2026-07-01..2026-07-31",
            "financial_engine_status": "LEGACY_FALLBACK",
            "finance_api_status": "FORBIDDEN",
            "official_new_finance_available": False,
            "sales_for_pay_total": 1000,
            "payment_received_total": 900,
            "official_net_profit": None,
            "risks": ["Официальные данные ещё не подтверждены."],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_products_center_snapshot",
        lambda user, days: {
            "sku_registry_status": "WARNING",
            "cost_coverage_percent": 82.5,
            "known_skus": 12,
            "missing_skus": 4,
            "critical_stock_count": 2,
            "stock_snapshot_date": "2026-07-03",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_analytics_center_snapshot",
        lambda user, days: {
            "sales_available": "OK",
            "ads_available": "WARNING",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_system_center_snapshot",
        lambda user, days: {
            "agent_status": "OK",
            "product_readiness": "WARNING",
            "structure_status": "READY",
            "known_blockers": [],
            "engineering_commands": [],
        },
    )
    monkeypatch.setattr(telegram_bot, "has_permission", lambda user_id, permission: False)
    monkeypatch.setattr(telegram_bot, "get_user", lambda _user_id: None)

    surfaces = [
        telegram_bot._start_text(),
        telegram_bot._main_menu_text(),
        telegram_bot._customer_profile_text((1, "demo", "", "FREE", None, None, None, "owner", None), "@demo", 1),
        telegram_bot._home_text(1, ("2026-07-01", "2026-07-31")),
        telegram_bot._business_center_text(1, ("2026-07-01", "2026-07-31")),
        telegram_bot._finance_center_text(1, ("2026-07-01", "2026-07-31")),
        telegram_bot._products_center_text(1, ("2026-07-01", "2026-07-31")),
        telegram_bot._analytics_center_text(1, ("2026-07-01", "2026-07-31")),
        telegram_bot._system_center_text(1, ("2026-07-01", "2026-07-31")),
    ]

    for text in surfaces:
        assert "????" not in text
        assert "Wildberries Agent" not in text
        assert "Legacy fallback" not in text
        assert "/help developer" not in text
