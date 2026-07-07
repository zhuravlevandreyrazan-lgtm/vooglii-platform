from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_telegram.ux.financial_modes import FinancialMode, financial_mode_hint, financial_mode_label, validation_summary_text


def test_financial_mode_labels_and_hints():
    assert financial_mode_label(FinancialMode.MANAGEMENT_PNL) == "Управленческий P&L"
    assert financial_mode_label(FinancialMode.WB_WEEKLY_PARITY) == "Сверка с официальным отчётом WB"
    assert "/finance validate" in financial_mode_hint(FinancialMode.MANAGEMENT_PNL)
    assert "не управленческий P&L" in financial_mode_hint(FinancialMode.WB_WEEKLY_PARITY)


def test_management_reports_show_mode_labels(monkeypatch):
    monkeypatch.setattr(
        "vooglii_finance.unified_snapshot.build_unified_financial_snapshot_dict",
        lambda *_args, **_kwargs: {
            "orders_count": 10,
            "sales_count": 8,
            "returns_count": 2,
            "sales_revenue": 1000.0,
            "wb_payout": 700.0,
            "wb_payments_received": 650.0,
            "cost_price": 400.0,
            "advertising_spend": 50.0,
            "logistics": 20.0,
            "storage": 5.0,
            "acquiring": 3.0,
            "wb_deductions": 10.0,
            "other_expenses": 2.0,
            "expenses_total": 490.0,
            "tax_amount": 50.0,
            "margin_percent": 21.0,
            "roi_percent": 30.0,
            "drr_percent": 5.0,
            "roas": 20.0,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
            "advertising_status": "ADS_OK",
            "cost_status": "COST_OK",
            "cost_coverage_percent": 100.0,
            "profit_display_mode": "FINAL",
            "net_profit": 210.0,
            "profit_before_tax": 260.0,
        },
    )
    monkeypatch.setattr(telegram_bot, "_unified_finance_bot", lambda: telegram_bot)
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")
    monkeypatch.setattr(telegram_bot, "_customer_finance_status_label", lambda *_args, **_kwargs: "подтверждено")
    monkeypatch.setattr(telegram_bot, "_customer_ads_status_label", lambda *_args, **_kwargs: "OK")
    monkeypatch.setattr(telegram_bot, "_customer_cost_status_label", lambda *_args, **_kwargs: "OK")
    monkeypatch.setattr(telegram_bot, "_customer_cost_value_text", lambda *_args, **_kwargs: "400.00 ₽")
    monkeypatch.setattr(telegram_bot, "_customer_finance_waiting_note", lambda *_args, **_kwargs: "Финансовые данные подтверждены.")
    monkeypatch.setattr("vooglii_telegram.ux.financial_modes.get_latest_validation_result", lambda _user_id: None)

    report_text = telegram_bot._unified_report_text(42, ("2026-06-29", "2026-07-05"))
    pnl_text = telegram_bot._pnl_customer_text(42, ("2026-06-29", "2026-07-05"))

    assert "Режим:" in report_text
    assert "Управленческий P&L" in report_text
    assert "/finance validate" in report_text
    assert "Режим:" in pnl_text
    assert "Управленческий P&L" in pnl_text


def test_validation_summary_text_without_history(monkeypatch):
    monkeypatch.setattr("vooglii_telegram.ux.financial_modes.get_latest_validation_result", lambda _user_id: None)

    text = validation_summary_text(42, compact=True)

    assert text == "Сверка WB: ещё не выполнялась"
