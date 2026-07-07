from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def test_finance_and_home_show_latest_validation_summary(monkeypatch):
    monkeypatch.setattr(
        "vooglii_telegram.ux.financial_modes.get_latest_validation_result",
        lambda _user_id: {
            "period_from": "2026-06-29",
            "period_to": "2026-07-05",
            "status": "PASS",
            "parity_score": 99.7,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_home_snapshot",
        lambda user, days: {
            "period_label": "29.06.2026 - 05.07.2026",
            "sales_status": "OK",
            "finance_status": "FINANCE_OK",
            "ads_status": "ADS_OK",
            "costs_status": "COST_OK",
            "cost_value": 100.0,
            "cost_coverage_percent": 100.0,
            "wb_connected": True,
        },
    )
    monkeypatch.setattr(telegram_bot, "main_sections", lambda: ["/business", "/finance"])
    monkeypatch.setattr(telegram_bot, "_customer_sales_status_label", lambda _status: "OK")
    monkeypatch.setattr(telegram_bot, "_customer_finance_status_label", lambda _status: "OK")
    monkeypatch.setattr(telegram_bot, "_customer_ads_status_label", lambda _status: "OK")
    monkeypatch.setattr(telegram_bot, "_customer_cost_status_label", lambda *_args, **_kwargs: "OK")
    monkeypatch.setattr(
        telegram_bot,
        "_finance_center_snapshot",
        lambda user, days: {
            "finance_status": "FINANCE_OK",
            "finance_status_text": "OK",
            "sales_for_pay_total": 700.0,
            "payment_received_total": 650.0,
            "advertising_total": 50.0,
            "cost_price_total": 200.0,
            "logistics_total": 20.0,
            "storage_total": 5.0,
            "deductions_total": 10.0,
            "acquiring_total": 3.0,
            "other_expenses_total": 2.0,
            "expenses_total": 290.0,
            "unknown_wb_expenses_total": None,
            "coverage_percent": 100.0,
            "unified_snapshot": {
                "finance_confidence": "HIGH",
                "cost_status": "COST_OK",
                "cost_coverage_percent": 100.0,
                "profit_display_mode": "FINAL",
                "reconciliation_delta": None,
                "confirmed_expenses_total": 250.0,
                "pending_expenses_total": 40.0,
            },
            "profit_total": 210.0,
        },
    )
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")
    monkeypatch.setattr(telegram_bot, "_customer_cost_status_label", lambda *_args, **_kwargs: "OK")
    monkeypatch.setattr(telegram_bot, "_customer_cost_value_text", lambda *_args, **_kwargs: "200.00 ₽")
    monkeypatch.setattr(telegram_bot, "_customer_confirmed_pending_expense_lines", lambda *_args, **_kwargs: [])

    home_text = telegram_bot._home_text(42, ("2026-06-29", "2026-07-05"))
    finance_text = telegram_bot._finance_center_text(42, ("2026-06-29", "2026-07-05"))

    assert "Сверка WB: PASS 99.7%" in home_text
    assert "Сверка с WB:" in finance_text
    assert "Совпадение: 99.7%" in finance_text
