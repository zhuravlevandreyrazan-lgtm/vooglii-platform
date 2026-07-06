from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


def _patch_period_sources(monkeypatch):
    monkeypatch.setattr(
        telegram_bot,
        "_center_days",
        lambda days: {
            "today": ("2026-07-07", "2026-07-07"),
            "week": ("2026-07-01", "2026-07-07"),
            "month": ("2026-07-01", "2026-07-31"),
        }.get(days, days),
    )
    monkeypatch.setattr(
        telegram_bot,
        "_period_dates",
        lambda days: days if isinstance(days, tuple) else telegram_bot._center_days(days),
    )
    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, days, context=None: {
            "revenue": 110000.0,
            "payout": 83000.0,
            "cost_price": 42000.0,
            "advertising": 21000.0,
            "logistics": 5100.0,
            "storage": 900.0,
            "other": 400.0,
            "acquiring": 250.0,
            "deductions": 700.0,
            "unexplained": 0.0,
            "period_start": days[0] if isinstance(days, tuple) else "2026-07-01",
            "period_end": days[1] if isinstance(days, tuple) else "2026-07-31",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": True,
            "official_net_profit": 29650.0,
            "status": "OK",
            "cost_total": 42000.0,
            "tax_amount": 10000.0,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": 83000.0,
            "sales_for_pay_total": 83000.0,
            "sales_revenue_total": 110000.0,
            "status": "OK",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None: {
            "coverage_percent": 100.0,
            "logistics": 5100.0,
            "storage": 900.0,
            "acquiring": 250.0,
            "deductions": 700.0,
            "explicit_other_deductions": 400.0,
            "other_deductions": 400.0,
            "residual_other_deductions": 0.0,
            "unexplained_total": 0.0,
            "status": "OK",
        },
    )
    monkeypatch.setattr(telegram_bot, "_finance_api_status_snapshot", lambda _user: {"status": "OK"})
    monkeypatch.setattr(telegram_bot, "_advertising_customer_snapshot", lambda _user, _days: {"normalized_status": "ADS_OK", "status_kind": "ready", "total_spend": 21000.0})
    monkeypatch.setattr(telegram_bot, "_products_center_snapshot", lambda user=None, days=None, **kwargs: {"cost_coverage_percent": 100.0, "known_skus": 12, "missing_skus": 0, "critical_stock_count": 0})
    monkeypatch.setattr(telegram_bot, "_data_quality_snapshot", lambda _user, _days, context=None: {"overall_status": "HIGH", "sales": {"status": "OK"}})
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (15, 121000.0, 1, 5000.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (13, 110000.0))
    monkeypatch.setattr(telegram_bot, "get_profit_stats", lambda _days, _user: (110000.0, 2500.0, 83000.0, 42000.0, 5100.0, 21000.0, 900.0, 400.0, 70350.0, 0.0, 39650.0, 27.0, 2))
    monkeypatch.setattr(telegram_bot, "get_profit_stats_after_tax", lambda _days, _user: {"profit_before_tax": 39650.0, "tax": 10000.0, "profit_after_tax": 29650.0, "margin_after_tax": 27.0, "tax_configured": True})


@pytest.mark.parametrize(
    "days",
    [
        "today",
        "week",
        "month",
        ("2026-05-01", "2026-05-31"),
        ("2026-06-01", "2026-06-30"),
        ("2026-07-01", "2026-07-31"),
        ("2026-07-10", "2026-07-17"),
    ],
)
def test_financial_core_builds_consistently_for_supported_periods(monkeypatch, days):
    _patch_period_sources(monkeypatch)
    snapshot = build_unified_financial_snapshot_dict(100, days, bot=telegram_bot)

    assert snapshot["source_map"]
    assert snapshot["sales_revenue"] == 110000.0
    assert snapshot["advertising_spend"] == 21000.0
    assert snapshot["expenses_total"] == 70350.0
    assert snapshot["net_profit"] == 29650.0
    assert snapshot["finance_status"] == "FINANCE_OK"
    assert snapshot["finance_confidence"] == "HIGH"

    report_text = telegram_bot._unified_report_text(100, days)
    finance_text = telegram_bot._finance_center_text(100, days)
    pnl_text = telegram_bot._pnl_customer_text(100, days)

    assert report_text
    assert finance_text
    assert pnl_text
    assert "110 000.00" in report_text
    assert "21 000.00" in finance_text
    assert "70 350.00" in pnl_text
