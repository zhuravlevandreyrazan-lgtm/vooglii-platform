from __future__ import annotations

import telegram_bot
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


TEST_USER_ID = 658486226
TEST_DAYS = ("2026-05-01", "2026-05-31")


def test_unified_snapshot_matches_may_2026_profit_audit_baseline(monkeypatch):
    old_profit_components = {
        "revenue": 823526.23,
        "wb_payout": 480472.04,
        "cost": 294253.00,
        "ads": 29900.63,
        "logistics": 18123.45,
        "storage": 5120.10,
        "acquiring": 3421.12,
        "deductions": 7845.33,
        "other": 2630.44,
    }

    monkeypatch.setattr(
        telegram_bot,
        "_report_mgmt_snapshot",
        lambda _user, _days, context=None: {
            "revenue": 0.0,
            "payout": 0.0,
            "cost_price": 0.0,
            "advertising": 0.0,
            "logistics": 0.0,
            "storage": 0.0,
            "acquiring": 0.0,
            "deductions": 0.0,
            "other": 0.0,
            "unexplained": 0.0,
            "period_start": TEST_DAYS[0],
            "period_end": TEST_DAYS[1],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats",
        lambda _days, _user: (
            old_profit_components["revenue"],
            round(old_profit_components["revenue"] - old_profit_components["wb_payout"], 2),
            old_profit_components["wb_payout"],
            old_profit_components["cost"],
            0.0,
            old_profit_components["ads"],
            0.0,
            0.0,
            old_profit_components["ads"],
            round(old_profit_components["wb_payout"] - old_profit_components["cost"], 2),
            round(old_profit_components["wb_payout"] - old_profit_components["cost"] - old_profit_components["ads"], 2),
            0.0,
            0,
        ),
    )
    monkeypatch.setattr(
        telegram_bot,
        "_financial_engine_snapshot",
        lambda _start, _end, user=None, context=None: {
            "official_new_finance_available": True,
            "status": "MATCHED",
            "cost_total": 294253.00,
            "logistics_total": old_profit_components["logistics"],
            "storage_total": old_profit_components["storage"],
            "payment_services_commission_total": old_profit_components["acquiring"],
            "deductions_total": old_profit_components["deductions"],
            "tax_amount": 49411.57,
            "official_net_profit": 136807.47,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "get_finance_difference_snapshot",
        lambda _user, _start, _end, context=None: {
            "coverage_percent": 100.0,
            "real_coverage_percent": 100.0,
            "logistics": old_profit_components["logistics"],
            "storage": old_profit_components["storage"],
            "acquiring": old_profit_components["acquiring"],
            "deductions": old_profit_components["deductions"],
            "explicit_other_deductions": old_profit_components["other"],
            "other_deductions": old_profit_components["other"],
            "residual_other_deductions": 910.22,
            "status": "HIGH",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_payment_reconciliation_snapshot",
        lambda _user, _start, _end, context=None: {
            "weekly_payout_total_all": old_profit_components["wb_payout"],
            "sales_for_pay_total": old_profit_components["wb_payout"],
            "sales_revenue_total": old_profit_components["revenue"],
            "status": "OK",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_advertising_customer_snapshot",
        lambda _user, _days: {
            "normalized_status": "ADS_OK",
            "status_kind": "ready",
            "total_spend": old_profit_components["ads"],
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_products_center_snapshot",
        lambda user=None, days=None, **kwargs: {
            "cost_coverage_percent": 100.0,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_finance_api_status_snapshot",
        lambda _user: {
            "status": "OK",
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_data_quality_snapshot",
        lambda _user, _days, context=None: {
            "overall_status": "HIGH",
        },
    )
    monkeypatch.setattr(telegram_bot, "get_orders_stats", lambda _days, _user: (0, 0.0, 0, 0.0))
    monkeypatch.setattr(telegram_bot, "get_period_stats", lambda _days, _user: (0, old_profit_components["revenue"]))
    monkeypatch.setattr(
        telegram_bot,
        "get_profit_stats_after_tax",
        lambda _days, _user: {
            "profit_before_tax": 0.0,
            "tax": 49411.57,
            "profit_after_tax": 136807.47,
            "tax_configured": True,
        },
    )
    monkeypatch.setattr(
        telegram_bot,
        "_profit_audit_snapshot",
        lambda _user, _days, context=None: {
            "period_start": TEST_DAYS[0],
            "period_end": TEST_DAYS[1],
            "official_financial_profit": {
                "cost_total": 294253.00,
                "tax_amount": 49411.57,
                "official_net_profit": 136807.47,
            },
            "profit_reconciliation_debug": {
                "components": dict(old_profit_components),
            },
            "finance_health": {
                "logistics": old_profit_components["logistics"],
                "storage": old_profit_components["storage"],
                "acquiring": old_profit_components["acquiring"],
                "deductions": old_profit_components["deductions"],
                "explicit_other_deductions": old_profit_components["other"],
            },
        },
    )

    unified = build_unified_financial_snapshot_dict(TEST_USER_ID, TEST_DAYS, bot=telegram_bot)
    profit_audit = telegram_bot._profit_audit_snapshot(TEST_USER_ID, TEST_DAYS)
    components = (profit_audit.get("profit_reconciliation_debug") or {}).get("components") or {}

    assert unified["sales_revenue"] == components["revenue"]
    assert unified["wb_payout"] == components["wb_payout"]
    assert unified["cost_price"] == components["cost"]
    assert unified["advertising_spend"] == components["ads"]
    assert unified["logistics"] == components["logistics"]
    assert unified["storage"] == components["storage"]
    assert unified["acquiring"] == components["acquiring"]
    assert unified["wb_deductions"] == components["deductions"]
    assert unified["other_expenses"] == components["other"]
    assert unified["tax_amount"] == 49411.57
    assert unified["net_profit"] == 136807.47
    assert unified["finance_status"] == "FINANCE_OK"
    assert unified["cost_status"] == "COST_OK"
