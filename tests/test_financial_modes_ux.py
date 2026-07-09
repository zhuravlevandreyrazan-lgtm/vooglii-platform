from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_finance.customer_snapshot import FrozenSnapshot


def _closed_week_snapshot() -> FrozenSnapshot:
    return FrozenSnapshot(
        {
            "source_mode": "WB_NATIVE_CLOSED",
            "is_preliminary": False,
            "finance_status": "FINANCE_OK",
            "finance_confidence": "HIGH",
            "finance_confidence_score": 95.0,
            "sales_revenue": 14046.08,
            "wb_sale_amount": 14046.08,
            "wb_payout": 15327.09,
            "wb_payout_amount": 15327.09,
            "wb_total_to_pay": 9084.94,
            "logistics": 3463.06,
            "wb_logistics": 3463.06,
            "storage": 631.09,
            "wb_storage": 631.09,
            "acquiring": 558.14,
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
            "official_net_profit": None,
            "tax_amount": None,
            "expenses_total": 14384.53,
            "margin_percent": -2.4,
            "roi_percent": -4.5,
            "orders_count": 12,
            "buyouts_count": 10,
            "returns_count": 1,
            "advertising_status": "ADS_OK",
            "cost_status": "COST_OK",
            "wb_data_status_text": "Р”Р°РЅРЅС‹Рµ WB: рџџў РїРµСЂРёРѕРґ Р·Р°РєСЂС‹С‚",
            "warnings": ("РќР°Р»РѕРіРѕРІС‹Р№ СЂРµР¶РёРј РЅРµ РЅР°СЃС‚СЂРѕРµРЅ. Р§РёСЃС‚Р°СЏ РїСЂРёР±С‹Р»СЊ РїРѕСЃР»Рµ РЅР°Р»РѕРіР° РЅРµ СЂР°СЃСЃС‡РёС‚Р°РЅР°.",),
            "field_trace": {
                "expenses_total": {
                    "selected_source": "derived_sum",
                    "sum": 14384.53,
                },
                "operational_profit": {
                    "selected_source": "derived_sales_revenue_minus_expenses_total",
                    "sum": -338.45,
                },
            },
        }
    )


def test_closed_week_report_shows_uncomputed_net_profit(monkeypatch):
    snapshot = _closed_week_snapshot()
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")
    monkeypatch.setattr(telegram_bot, "_customer_cost_value_text", lambda *_args, **_kwargs: "5 407.00 в‚Ѕ")

    report_text = telegram_bot._unified_report_text(42, ("2026-06-29", "2026-07-05"))

    assert "Операционная прибыль: -338.45" in report_text
    assert "Чистая прибыль: не рассчитана" in report_text


def test_closed_week_finance_ux_uses_confirmed_wb_status_and_tax_note(monkeypatch):
    snapshot = _closed_week_snapshot()
    monkeypatch.setattr(telegram_bot, "_customer_financial_snapshot", lambda *_args, **_kwargs: snapshot)
    monkeypatch.setattr(telegram_bot, "_customer_period_label", lambda *_args, **_kwargs: "29.06.2026 - 05.07.2026")
    monkeypatch.setattr(telegram_bot, "_customer_cost_value_text", lambda *_args, **_kwargs: "5 407.00 в‚Ѕ")

    finance_text = telegram_bot._finance_center_text(42, ("2026-06-29", "2026-07-05"))

    assert "Финансовые данные WB ещё не подтверждены" not in finance_text
    assert "Налоговый режим не настроен" in finance_text
