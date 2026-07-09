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


class _Message:
    def __init__(self, text: str):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _Update:
    def __init__(self, text: str):
        self.message = _Message(text)
        self.effective_user = SimpleNamespace(id=42, username="owner")


class _Context:
    def __init__(self, args):
        self.args = list(args)


def _snapshot() -> FrozenSnapshot:
    return FrozenSnapshot(
        {
            "source_mode": "WB_NATIVE_CLOSED",
            "is_preliminary": False,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
            "sales_revenue": 14046.08,
            "wb_sale_amount": 14046.08,
            "wb_payout_amount": 15327.09,
            "wb_total_to_pay": 9084.94,
            "wb_logistics": 3463.06,
            "wb_storage": 631.09,
            "wb_acquiring": 558.14,
            "wb_deductions": 2148.00,
            "wb_other": 0.0,
            "other_expenses": 0.0,
            "penalties": 0.0,
            "advertising_spend": 2177.24,
            "advertising": 2177.24,
            "cost_price": 5407.00,
            "operational_profit": -338.45,
            "profit_before_tax": -338.45,
            "net_profit": None,
            "tax_amount": None,
            "expenses_total": 14384.53,
            "margin_percent": -2.4,
            "wb_data_status_text": "Данные WB: 🟢 период закрыт",
            "warnings": ("Налоговый режим не настроен. Чистая прибыль после налога не рассчитана.",),
            "field_trace": {},
        }
    )


def test_finance_command_uses_unified_renderer_for_default_and_date_period(monkeypatch):
    outputs: list[str] = []

    async def _send_long(update, text, **kwargs):
        outputs.append(str(text))

    monkeypatch.setattr(telegram_bot, "send_long", _send_long)
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: _snapshot())
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")

    asyncio.run(telegram_bot.finance_command(_Update("/finance"), _Context([])))
    asyncio.run(telegram_bot.finance_command(_Update("/finance 2026-06-29 2026-07-05"), _Context(["2026-06-29", "2026-07-05"])))

    assert len(outputs) == 2
    for text in outputs:
        assert "Главное:" in text
        assert "Деньги WB:" in text
        assert "Почему прибыль и выплата отличаются:" in text
        assert "Расходы бизнеса:" in text
        assert "Чистая прибыль:" in text
        assert "Чистая прибыль:\nне рассчитана" in text
        assert "Деньги:" not in text
