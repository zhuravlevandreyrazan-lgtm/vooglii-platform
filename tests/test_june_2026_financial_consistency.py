from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


TEST_USER_ID = 658486226
TEST_DAYS = ("2026-06-01", "2026-06-30")


def test_june_2026_customer_outputs_use_low_confidence_guardrails(monkeypatch):
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, _days, context=None: {
            "revenue": 22351.98,
            "payout": 22351.98,
            "cost_price": 0.0,
            "advertising": 29893.34,
            "logistics": 3463.65,
            "storage": 449.57,
            "acquiring": 6848.00,
            "deductions": 37484.00,
            "other": 2687.14,
            "unexplained": -41654.86,
            "period_start": TEST_DAYS[0],
            "period_end": TEST_DAYS[1],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": False,
            "official_net_profit": None,
            "status": "OFFICIAL_NEW_FINANCE_UNAVAILABLE",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": 0.0,
            "sales_for_pay_total": 22351.98,
            "sales_revenue_total": 22351.98,
            "status": "WAITING_WB",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None: {
            "coverage_percent": 0.0,
            "logistics": 3463.65,
            "storage": 449.57,
            "acquiring": 6848.00,
            "deductions": 37484.00,
            "explicit_other_deductions": 2687.14,
            "other_deductions": 2687.14,
            "residual_other_deductions": -41654.86,
            "unexplained_total": -41654.86,
            "status": "WAITING_WB",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_OK",
            "status_kind": "ready",
            "total_spend": 29893.34,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_products_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "cost_coverage_percent": 0.0,
            "known_skus": 0,
            "missing_skus": 10,
            "critical_stock_count": 0,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_business_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "business_health": "WARNING",
            "business_state": {"sales": "UNKNOWN", "finance": "BLOCKED", "ads": "GOOD"},
            "main_recommendation": "Не принимать решения по прибыли, пока достоверность финансового отчёта низкая.",
            "main_recommendation_action": "Открыть /finance.",
            "risks": ["Финансовые данные WB ещё не подтверждены"],
            "today_actions": ["Открыть /advisor"],
            "advertising": telegram_bot._advertising_customer_snapshot(user, days),
            "products": telegram_bot._products_center_snapshot(user, days),
            "unified_finance": build_unified_financial_snapshot_dict(user, days, bot=telegram_bot),
        },
    )
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "WAITING"})
    monkeypatch.setattr(telegram_bot, "_data_quality_snapshot", lambda _user, _days, context=None: {"overall_status": "HIGH"})
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (0, 0.0, 0, 0.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (0, 22351.98))
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats",
        lambda _days, _user: (
            22351.98,
            0.0,
            22351.98,
            0.0,
            3463.65,
            29893.34,
            449.57,
            2687.14,
            0.0,
            0.0,
            0.0,
            0.0,
            0,
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats_after_tax",
        lambda _days, _user: {
            "profit_before_tax": None,
            "tax": 0.0,
            "profit_after_tax": 0.0,
            "tax_configured": False,
        },
    )

    snapshot = build_unified_financial_snapshot_dict(TEST_USER_ID, TEST_DAYS, bot=telegram_bot)
    outputs = {
        "report": telegram_bot._unified_report_text(TEST_USER_ID, TEST_DAYS),
        "finance": telegram_bot._finance_center_text(TEST_USER_ID, TEST_DAYS),
        "pnl": telegram_bot._pnl_customer_text(TEST_USER_ID, TEST_DAYS),
        "business": telegram_bot._business_center_text(TEST_USER_ID, TEST_DAYS),
        "dashboard": telegram_bot._unified_dashboard_text(TEST_USER_ID, TEST_DAYS),
        "ceo": telegram_bot._unified_ceo_text(TEST_USER_ID, TEST_DAYS),
        "advisor": telegram_bot._advisor_customer_text(TEST_USER_ID, TEST_DAYS),
    }

    assert snapshot["finance_status"] == "FINANCE_WAITING_WB"
    assert snapshot["finance_confidence"] == "LOW"
    assert snapshot["finance_confidence_score"] == 30
    assert snapshot["profit_display_mode"] == "HIDDEN"
    assert snapshot["expenses_total"] == 80825.70
    assert snapshot["confirmed_expenses_total"] == 33806.56
    assert snapshot["pending_expenses_total"] == 47019.14
    assert snapshot["reconciliation_delta"] == -41654.86

    assert "будет рассчитана после подтверждения финансов WB" in outputs["report"]
    assert "Достоверность отчёта: низкая" in outputs["report"]
    assert "Чистая прибыль: -" not in outputs["report"]
    assert "Маржа: -" not in outputs["report"]
    assert "Операционная оценка до налога" not in outputs["report"]
    assert "ROI: не рассчитан" in outputs["report"]

    assert "Прибыль: будет рассчитана после подтверждения финансов WB" in outputs["finance"]
    assert "Предварительная операционная оценка" not in outputs["finance"]
    assert "Ожидают подтверждения WB:" in outputs["finance"]
    assert "Достоверность отчёта: низкая" in outputs["finance"]

    assert "P&L пока предварительный." in outputs["pnl"]
    assert "Прибыль, маржа и ROI будут рассчитаны после подтверждения финансов WB." in outputs["pnl"]

    assert "низкая" in outputs["business"].lower()
    assert "низкая" in outputs["dashboard"].lower()
    assert "отложить" in outputs["ceo"].lower() or "не подтвержд" in outputs["ceo"].lower()
    assert "не принимать решения по прибыли" in outputs["advisor"].lower()
