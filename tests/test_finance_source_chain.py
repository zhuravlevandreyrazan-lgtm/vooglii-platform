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


class _Message:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _Update:
    def __init__(self):
        self.message = _Message()
        self.effective_user = SimpleNamespace(id=42, username="owner")


def test_finance_explain_shows_documents_and_dates(monkeypatch):
    async def _access(*_args, **_kwargs):
        return True

    async def _send_long(update, text, **_kwargs):
        update.message.replies.append(str(text))

    monkeypatch.setattr(legacy_bot, "access", _access)
    monkeypatch.setattr(legacy_bot, "send_long", _send_long)
    monkeypatch.setattr(legacy_bot, "_unified_finance_bot", lambda: telegram_bot)
    monkeypatch.setattr(telegram_bot, "_center_days", lambda days: days)
    monkeypatch.setattr(telegram_bot, "_period_dates", lambda days: days)
    monkeypatch.setattr(
        __import__("vooglii_finance.unified_snapshot", fromlist=["build_unified_financial_snapshot_dict"]),
        "build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "sales_revenue": 100.0,
            "advertising_spend": 12.0,
            "logistics": 7.0,
            "storage": 1.0,
            "acquiring": 2.0,
            "wb_deductions": 3.0,
            "other_expenses": 4.0,
            "cost_price": 10.0,
            "expenses_total": 39.0,
            "net_profit": 61.0,
            "warnings": [],
            "source_map": {
                "sales_revenue": {"selected_source": "sales", "rows": 2, "unique_documents": 2, "source_min_date": "2026-05-01", "source_max_date": "2026-05-31"},
                "advertising_spend": {"source_table": "finance_expense_events", "rows": 3, "unique_documents": 3, "source_min_date": "2026-05-01", "source_max_date": "2026-05-31", "fallback": False},
                "logistics": {"source_table": "finance_expense_events", "rows": 4, "unique_documents": 4, "source_min_date": "2026-05-10", "source_max_date": "2026-05-31", "fallback": False},
                "storage": {"source_table": "legacy_fallback", "rows": 1, "unique_documents": 1, "source_min_date": "2026-05-01", "source_max_date": "2026-05-31", "fallback": True},
                "acquiring": {"source_table": "finance_expense_events", "rows": 2, "unique_documents": 2, "source_min_date": "2026-05-02", "source_max_date": "2026-05-30", "fallback": False},
                "wb_deductions": {"source_table": "finance_expense_events", "rows": 2, "unique_documents": 2, "source_min_date": "2026-05-02", "source_max_date": "2026-05-30", "fallback": False},
                "other_expenses": {"source_table": "finance_expense_events", "rows": 2, "unique_documents": 2, "source_min_date": "2026-05-02", "source_max_date": "2026-05-30", "fallback": False},
                "cost_price": {"selected_source": "products x sales"},
                "expenses_total": {"selected_source": "derived_sum"},
                "net_profit": {"selected_source": "financial_engine.official_net_profit"},
            },
        },
    )

    update = _Update()
    asyncio.run(legacy_bot.finance_explain_command(update, SimpleNamespace(args=[]), "Май 2026", ("2026-05-01", "2026-05-31"), 42))
    text = update.message.replies[-1]

    assert "Документов: 3" in text
    assert "Даты: 2026-05-01..2026-05-31" in text
    assert "Режим: normalized layer" in text
    assert "Режим: legacy fallback" in text


if __name__ == "__main__":
    test_finance_explain_shows_documents_and_dates(__import__("pytest").MonkeyPatch())
    print("FINANCE SOURCE CHAIN OK", flush=True)
