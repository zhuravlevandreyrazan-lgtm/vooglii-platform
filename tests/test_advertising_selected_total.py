from __future__ import annotations

from vooglii_finance import unified_snapshot


class _BotStub:
    def _center_days(self, days):
        return days

    def _period_dates(self, days):
        return "2026-07-01", "2026-07-07"

    def _report_mgmt_snapshot(self, *_args, **_kwargs):
        return {}

    def _advertising_customer_snapshot(self, *_args, **_kwargs):
        return {
            "normalized_status": "ADS_OK",
            "status_kind": "success",
            "total_spend": 0.0,
        }

    def _products_center_snapshot(self, *_args, **_kwargs):
        return {"cost_coverage_percent": 100.0}

    def _finance_api_status_snapshot(self, *_args, **_kwargs):
        return {"status": "AVAILABLE"}

    def _financial_engine_snapshot(self, *_args, **_kwargs):
        return {"official_new_finance_available": True}

    def _payment_reconciliation_snapshot(self, *_args, **_kwargs):
        return {}

    def get_finance_difference_snapshot(self, *_args, **_kwargs):
        return {"coverage_percent": 100.0}

    def _data_quality_snapshot(self, *_args, **_kwargs):
        return {"overall_status": "OK", "sales": {"status": "OK"}}

    def get_orders_stats(self, *_args, **_kwargs):
        return (0, 0.0, 0, 0.0)

    def get_period_stats(self, *_args, **_kwargs):
        return (0, 0.0)

    def get_profit_stats(self, *_args, **_kwargs):
        return ()

    def get_profit_stats_after_tax(self, *_args, **_kwargs):
        return {}

    def humanize_period_range(self, start, end):
        return f"{start}..{end}"


def test_minor_advertising_drift_uses_advertising_table(monkeypatch):
    bot = _BotStub()
    bot._advertising_customer_snapshot = lambda *_args, **_kwargs: {
        "normalized_status": "ADS_OK",
        "status_kind": "success",
        "total_spend": 2171.62,
    }
    monkeypatch.setattr(
        unified_snapshot,
        "get_normalized_expense_summary",
        lambda *_args, **_kwargs: {
            "rows_total": 1,
            "categories": {
                "advertising": {
                    "amount": 2171.92,
                    "rows": 1,
                    "source_tables": ["advertising"],
                    "source_types": ["selected_source"],
                }
            },
        },
    )

    snapshot = unified_snapshot.build_unified_financial_snapshot_dict(1, 7, bot=bot)
    source = snapshot["source_map"]["advertising_spend"]

    assert snapshot["advertising_spend"] == 2171.62
    assert source["selected_customer_total"] == 2171.62
    assert source["selected_source"] == "advertising_table"
    assert source["drift_status"] == "accepted_minor_drift"
    assert source["drift_amount"] == 0.3


def test_significant_advertising_drift_marks_source_for_review(monkeypatch):
    bot = _BotStub()
    bot._advertising_customer_snapshot = lambda *_args, **_kwargs: {
        "normalized_status": "ADS_OK",
        "status_kind": "success",
        "total_spend": 2171.62,
    }
    monkeypatch.setattr(
        unified_snapshot,
        "get_normalized_expense_summary",
        lambda *_args, **_kwargs: {
            "rows_total": 1,
            "categories": {
                "advertising": {
                    "amount": 2173.12,
                    "rows": 1,
                    "source_tables": ["advertising"],
                    "source_types": ["selected_source"],
                }
            },
        },
    )

    snapshot = unified_snapshot.build_unified_financial_snapshot_dict(1, 7, bot=bot)
    source = snapshot["source_map"]["advertising_spend"]

    assert snapshot["advertising_spend"] == 2173.12
    assert source["selected_source"] == "needs_review"
    assert source["drift_status"] == "significant_drift"
    assert source["drift_amount"] == 1.5
