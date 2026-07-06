from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


def _patch_common(monkeypatch, *, finance_status: str, official_ready: bool, reconciliation_delta: float | None, cost_price: float | None):
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, _days, context=None: {
            "revenue": 120000.0,
            "payout": 91000.0,
            "cost_price": 0.0 if cost_price is None else cost_price,
            "advertising": 29900.63,
            "logistics": 6300.0,
            "storage": 1200.0,
            "other": 500.0,
            "acquiring": 300.0,
            "deductions": 800.0,
            "unexplained": reconciliation_delta or 0.0,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": 70000.0,
            "sales_for_pay_total": 91000.0,
            "sales_revenue_total": 120000.0,
            "status": "OK",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": official_ready,
            "official_net_profit": 24336.1 if official_ready else None,
            "status": "OK" if official_ready else "OFFICIAL_NEW_FINANCE_UNAVAILABLE",
            "cost_total": cost_price,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None: {
            "coverage_percent": 100.0 if finance_status == "FINANCE_PARTIAL" else 0.0,
            "logistics": 6300.0,
            "storage": 1200.0,
            "acquiring": 300.0,
            "deductions": 800.0,
            "explicit_other_deductions": 500.0,
            "other_deductions": 500.0,
            "residual_other_deductions": reconciliation_delta or 0.0,
            "unexplained_total": reconciliation_delta or 0.0,
            "status": finance_status,
        },
    )
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "OK" if finance_status != "FINANCE_WAITING_WB" else "WAITING"})
    monkeypatch.setattr(telegram_bot, "_advertising_customer_snapshot", lambda _user, _days: {"normalized_status": "ADS_OK", "status_kind": "ready", "total_spend": 29900.63})
    monkeypatch.setattr(telegram_bot, "_products_center_snapshot", lambda user=None, days=None, **kwargs: {"cost_coverage_percent": 100.0 if cost_price else 0.0, "missing_skus": 0 if cost_price else 10, "critical_stock_count": 0})
    monkeypatch.setattr(telegram_bot, "_data_quality_snapshot", lambda _user, _days, context=None: {"overall_status": "HIGH"})
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (18, 135000.0, 2, 7000.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (14, 120000.0))
    monkeypatch.setattr(telegram_bot, "get_profit_stats", lambda _days, _user: (120000.0, 3000.0, 91000.0, cost_price or 0.0, 6300.0, 29900.63, 1200.0, 500.0, 0.0, 0.0, 0.0, 0.0, 3))
    monkeypatch.setattr(telegram_bot, "get_profit_stats_after_tax", lambda _days, _user: {"profit_before_tax": 0.0, "tax": 10000.0 if official_ready else 0.0, "profit_after_tax": 24336.1 if official_ready else 0.0, "tax_configured": official_ready})


def test_finance_confidence_low_hides_final_profit(monkeypatch):
    _patch_common(monkeypatch, finance_status="FINANCE_WAITING_WB", official_ready=False, reconciliation_delta=-41654.86, cost_price=None)
    snapshot = build_unified_financial_snapshot_dict(100, ("2026-06-01", "2026-06-30"), bot=telegram_bot)
    report_text = telegram_bot._unified_report_text(100, ("2026-06-01", "2026-06-30"))
    finance_text = telegram_bot._finance_center_text(100, ("2026-06-01", "2026-06-30"))
    pnl_text = telegram_bot._pnl_customer_text(100, ("2026-06-01", "2026-06-30"))

    assert snapshot["finance_confidence"] == "LOW"
    assert snapshot["profit_display_mode"] == "HIDDEN"
    assert "Достоверность отчёта: низкая" in report_text
    assert "Прибыль будет рассчитана после подтверждения финансов WB" in report_text
    assert "Чистая прибыль: -" not in report_text
    assert "Маржа: -" not in report_text
    assert "ROI: -" not in report_text
    assert "Прибыль: будет рассчитана после подтверждения финансов WB" in finance_text
    assert "P&L пока предварительный." in pnl_text


def test_finance_confidence_medium_shows_preliminary_label(monkeypatch):
    _patch_common(monkeypatch, finance_status="FINANCE_PARTIAL", official_ready=False, reconciliation_delta=None, cost_price=45000.0)
    snapshot = build_unified_financial_snapshot_dict(100, ("2026-07-01", "2026-07-31"), bot=telegram_bot)
    report_text = telegram_bot._unified_report_text(100, ("2026-07-01", "2026-07-31"))

    assert snapshot["finance_confidence"] == "MEDIUM"
    assert snapshot["profit_display_mode"] == "PRELIMINARY"
    assert "Предварительная операционная оценка" in report_text
    assert "Чистая прибыль: будет рассчитана после подтверждения финансов WB" in report_text


def test_finance_confidence_high_shows_final_profit(monkeypatch):
    _patch_common(monkeypatch, finance_status="FINANCE_OK", official_ready=True, reconciliation_delta=None, cost_price=45000.0)
    snapshot = build_unified_financial_snapshot_dict(100, ("2026-07-01", "2026-07-31"), bot=telegram_bot)
    report_text = telegram_bot._unified_report_text(100, ("2026-07-01", "2026-07-31"))

    assert snapshot["finance_confidence"] == "HIGH"
    assert snapshot["profit_display_mode"] == "FINAL"
    assert "Прибыль до налога:" in report_text
    assert "Чистая прибыль: 24 336.10" in report_text
