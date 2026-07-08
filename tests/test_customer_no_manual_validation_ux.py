from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_finance.customer_snapshot import FrozenSnapshot
from vooglii_telegram.handlers.finance import finance_command
from vooglii_telegram.handlers.validate import validate_command


class _Message:
    def __init__(self):
        self.texts: list[str] = []

    async def reply_text(self, text):
        self.texts.append(text)


class _Bot:
    async def access(self, update, permission):
        return True

    def uid(self, _update):
        return 42

    def _is_engineering_role(self, _user_id):
        return False

    async def _finance_command_entry(self, update, context):
        await update.message.reply_text("finance fallback")


def test_customer_commands_do_not_show_manual_validation(monkeypatch):
    monkeypatch.setattr("vooglii_telegram.handlers.finance.get_bot", lambda: _Bot())
    monkeypatch.setattr("vooglii_telegram.handlers.validate.get_bot", lambda: _Bot())
    update_finance = SimpleNamespace(message=_Message())
    update_validate = SimpleNamespace(message=_Message())

    asyncio.run(finance_command(update_finance, SimpleNamespace(args=["validate"])))
    asyncio.run(validate_command(update_validate, SimpleNamespace(args=[])))

    assert "автоматически" in update_finance.message.texts[0].lower()
    assert "/report" in update_finance.message.texts[0]
    assert "автоматически" in update_validate.message.texts[0].lower()
    assert "загрузите" not in update_validate.message.texts[0].lower()


def test_customer_report_has_no_manual_validation_copy(monkeypatch):
    monkeypatch.setattr(
        telegram_bot,
        "_customer_financial_snapshot",
        lambda *_args, **_kwargs: FrozenSnapshot({
            "orders_count": 10,
            "buyouts_count": 8,
            "returns_count": 2,
            "sales_revenue": 1200.0,
            "wb_sale_amount": 1200.0,
            "wb_payout": 900.0,
            "wb_payout_amount": 900.0,
            "logistics": 40.0,
            "wb_logistics": 40.0,
            "storage": 5.0,
            "wb_storage": 5.0,
            "acquiring": 3.0,
            "wb_acquiring": 3.0,
            "wb_deductions": 10.0,
            "wb_total_to_pay": 850.0,
            "advertising_spend": 50.0,
            "advertising": 50.0,
            "cost_price": 400.0,
            "profit_before_tax": 200.0,
            "operational_profit": 200.0,
            "net_profit": None,
            "finance_status": "FINANCE_WAITING_WB",
            "finance_confidence": "LOW",
            "source_mode": "OPERATIONAL_PRELIMINARY",
            "is_preliminary": True,
            "wb_data_status_text": "Данные WB: 🟡 данные обновляются",
            "field_trace": {},
        }),
    )
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "07.07.2026 - 08.07.2026")

    text = telegram_bot._unified_report_text(42, ("2026-07-07", "2026-07-08"))

    assert "Режим:" not in text
    assert "/finance validate" not in text
    assert "загрузите недельный отчёт wb" not in text.lower()
