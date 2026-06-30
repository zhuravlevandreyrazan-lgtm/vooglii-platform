"""Readonly regression test for finance component overlap / double-count risk."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


class _FakeCursor:
    def __init__(self):
        self._result = None
        self._rows = []

    def execute(self, query, params=None):
        text = str(query or "")
        if "FROM finance_raw_audit" in text and "COUNT(*)," in text:
            self._result = (1, 10.00, 0.0, 0.0, 0.0)
            self._rows = []
        elif "FROM expenses" in text:
            self._result = (0,)
            self._rows = []
        else:
            self._result = (0,)
            self._rows = []
        return self

    def fetchone(self):
        return self._result

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def close(self):
        return None


def main():
    originals = {
        "get_profit_stats": telegram_bot.get_profit_stats,
        "_finance_local_expenses_analysis": telegram_bot._finance_local_expenses_analysis,
        "_finance_raw_article_details": telegram_bot._finance_raw_article_details,
        "_finance_bucket_debug": telegram_bot._finance_bucket_debug,
        "sqlite3_connect": telegram_bot.sqlite3.connect,
        "_report_mgmt_snapshot": telegram_bot._report_mgmt_snapshot,
        "_data_quality_snapshot": telegram_bot._data_quality_snapshot,
        "_advertising_health_snapshot": telegram_bot._advertising_health_snapshot,
        "_finance_wbdelta_snapshot": telegram_bot._finance_wbdelta_snapshot,
        "_stale_sync_warnings": telegram_bot._stale_sync_warnings,
        "calculate_tax": telegram_bot.calculate_tax,
        "_financial_engine_snapshot": telegram_bot._financial_engine_snapshot,
        "_official_financial_profit_snapshot": telegram_bot._official_financial_profit_snapshot,
        "_finance_reconcile_snapshot": telegram_bot._finance_reconcile_snapshot,
    }
    try:
        telegram_bot.get_profit_stats = lambda period, user: (
            311708.48,
            88769.01,
            222939.47,
            100000.00,
            59833.62,
            5000.00,
            2686.16,
            39563.00,
        )
        telegram_bot._finance_local_expenses_analysis = lambda user, period: {
            "st": telegram_bot.get_profit_stats(period, user),
            "acquiring": 8712.48,
            "deduction": 39563.00,
            "other_local": 0.0,
            "penalties": 10.00,
            "hidden_difference": 0.0,
            "after": {"tax_configured": True, "tax": 1000.0, "tax_warning": None},
        }
        telegram_bot._finance_raw_article_details = lambda user, start_date, end_date: {"rows": [], "bucket_totals": {}}
        telegram_bot._finance_bucket_debug = lambda raw_article_debug, wb_difference, residual_other_deductions: {}
        telegram_bot.sqlite3.connect = lambda *args, **kwargs: _FakeConnection()
        telegram_bot._report_mgmt_snapshot = lambda user, days, context=None: {
            "period_start": "2026-06-01",
            "period_end": "2026-06-28",
            "revenue": 311708.48,
            "payout": 222939.47,
            "cost_price": 100000.00,
            "advertising": 5000.00,
            "storage": 2686.16,
            "logistics": 59833.62,
            "other": 39563.00,
            "acquiring": 8712.48,
            "deductions": 39563.00,
            "external_expenses": 0.0,
            "wb_difference": 88769.01,
            "unexplained": 0.0,
            "official_profit": 15856.69,
            "management_profit": 117939.47,
            "management_profit_with_storage": 115253.31,
            "management_margin": 52.9,
            "management_roi": 112.3,
            "delta": 102082.78,
            "quality": {"sales quality": "HIGH", "orders quality": "HIGH", "advertising quality": "HIGH", "finance quality": "HIGH"},
            "quality_snapshot": {"overall_status": "HIGH", "sales": {"status": "HIGH"}},
            "quality_critical": False,
            "recommended_profit": 115253.31,
            "warnings": [],
            "issues": [],
        }
        telegram_bot._data_quality_snapshot = lambda user, days, context=None: {
            "overall_status": "HIGH",
            "overall_score": 92.0,
            "sales": {"status": "HIGH"},
            "orders": {"status": "HIGH"},
            "advertising": {"status": "HIGH"},
            "finance": {"status": "HIGH"},
        }
        telegram_bot._advertising_health_snapshot = lambda user, days, context=None: {
            "status": "HIGH",
            "duplicate_negative_spend": 0.0,
            "duplicate_negative_rows": 0,
            "stale": False,
            "stale_critical": False,
            "negative_nm_id_rows": 0,
            "linkability_percent": 100.0,
        }
        telegram_bot._finance_wbdelta_snapshot = lambda user, days: {"likely_double_count_articles": []}
        telegram_bot._stale_sync_warnings = lambda user: []
        telegram_bot.calculate_tax = lambda user, revenue, profit: {"tax": 1000.0, "warning": None}
        telegram_bot._financial_engine_snapshot = lambda start_date, end_date, user=None, context=None: {
            "status": "MATCHED",
            "ads_handling": "UNKNOWN",
            "official_net_profit": -2500.0,
        }
        telegram_bot._official_financial_profit_snapshot = lambda start_date, end_date, user=None: {
            "status": "AVAILABLE",
            "official_net_profit": -2500.0,
        }
        telegram_bot._finance_reconcile_snapshot = lambda user, days: {
            "reconciliation": {
                "actual_formula": 0.0,
                "payout_bridge": 0.0,
                "payout_delta": 0.0,
            }
        }

        finance_snapshot = telegram_bot.get_finance_difference_snapshot(1, "2026-06-01", "2026-06-28", context={})
        _assert(float(finance_snapshot.get("wb_difference") or 0) == 88769.01, "wb_difference mismatch")
        _assert(float(finance_snapshot.get("explained_total") or 0) > float(finance_snapshot.get("wb_difference_abs") or 0), "explained_total should exceed wb_difference")
        _assert(bool(finance_snapshot.get("is_overexplained")) is True, "overexplained should be true")
        _assert(bool(finance_snapshot.get("finance_confirmed_double_count_risk")) is True, "confirmed double count risk should be true")
        _assert(str(finance_snapshot.get("reconciliation_status") or "") == "OVEREXPLAINED", "reconciliation_status should be OVEREXPLAINED")
        _assert(any("informational only" in str(item).lower() for item in finance_snapshot.get("warnings") or []), "overlap warning missing")

        mgmt = telegram_bot._report_mgmt_snapshot(1, ("2026-06-01", "2026-06-28"), context={})
        profit_display = telegram_bot._profit_display_snapshot(1, ("2026-06-01", "2026-06-28"), mgmt=mgmt, finance_health=finance_snapshot, after={"tax_configured": True, "tax": 1000.0})
        payout_verification = telegram_bot._payout_verification_snapshot(
            1,
            ("2026-06-01", "2026-06-28"),
            mgmt=mgmt,
            finance_health=finance_snapshot,
            profit_display=profit_display,
            reconcile_snapshot=telegram_bot._finance_reconcile_snapshot(1, ("2026-06-01", "2026-06-28")),
        )
        _assert(str(payout_verification.get("recommended_profit_base") or "") == "forPay - cost - advertising - external_expenses - tax", "recommended profit base mismatch")
        _assert(str(payout_verification.get("status") or "") in ("DEGRADED", "UNVERIFIED"), "payout verification status should be degraded/unverified")
        _assert(str(payout_verification.get("reconciliation_status") or "") in ("OVEREXPLAINED", "COMPONENT_OVERLAP", "UNVERIFIED", "DEGRADED", "NEEDS_REVIEW"), "unexpected reconciliation status")
        _assert(str(payout_verification.get("official_profit_status") or "") == "UNRECONCILED", "official profit status should be UNRECONCILED")
        _assert(str(payout_verification.get("management_profit_status") or "") == "OPERATIONAL", "management profit status should stay OPERATIONAL")
        _assert(any("do not subtract wb-side components" in str(item).lower() for item in payout_verification.get("warnings") or []), "double subtraction warning missing")

        profit_snapshot = telegram_bot._profit_audit_snapshot(1, ("2026-06-01", "2026-06-28"), context={})
        _assert(str(profit_snapshot.get("reconciliation_status") or "") in ("OVEREXPLAINED", "COMPONENT_OVERLAP", "UNVERIFIED", "DEGRADED"), "profit audit reconciliation_status unexpected")
        _assert(int(profit_snapshot.get("trust_score") or 0) < 80, "trust score should be reduced")
        _assert(str(profit_snapshot.get("official_profit_status") or "") == "UNRECONCILED", "profit audit official status should be UNRECONCILED")
        _assert(str(profit_snapshot.get("management_profit_status") or "") == "OPERATIONAL", "profit audit management status should be OPERATIONAL")
        _assert(any("operational payout model" in str(item).lower() for item in profit_snapshot.get("warnings") or []), "operational payout model warning missing")

        print("DOUBLE COUNT RECONCILIATION TEST OK")
    finally:
        telegram_bot.get_profit_stats = originals["get_profit_stats"]
        telegram_bot._finance_local_expenses_analysis = originals["_finance_local_expenses_analysis"]
        telegram_bot._finance_raw_article_details = originals["_finance_raw_article_details"]
        telegram_bot._finance_bucket_debug = originals["_finance_bucket_debug"]
        telegram_bot.sqlite3.connect = originals["sqlite3_connect"]
        telegram_bot._report_mgmt_snapshot = originals["_report_mgmt_snapshot"]
        telegram_bot._data_quality_snapshot = originals["_data_quality_snapshot"]
        telegram_bot._advertising_health_snapshot = originals["_advertising_health_snapshot"]
        telegram_bot._finance_wbdelta_snapshot = originals["_finance_wbdelta_snapshot"]
        telegram_bot._stale_sync_warnings = originals["_stale_sync_warnings"]
        telegram_bot.calculate_tax = originals["calculate_tax"]
        telegram_bot._financial_engine_snapshot = originals["_financial_engine_snapshot"]
        telegram_bot._official_financial_profit_snapshot = originals["_official_financial_profit_snapshot"]
        telegram_bot._finance_reconcile_snapshot = originals["_finance_reconcile_snapshot"]


if __name__ == "__main__":
    main()
