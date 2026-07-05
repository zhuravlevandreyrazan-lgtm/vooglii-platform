from __future__ import annotations

from pathlib import Path

import config
import db_manager
import telegram_bot
import report
import vooglii_telegram.legacy_bot as legacy_bot
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict


TEST_USER_ID = 658486226
TEST_DAYS = ("2026-05-01", "2026-05-31")
LIVE_DB = str((Path(__file__).resolve().parent.parent / "storage" / "wildberries.db").resolve())


def test_unified_snapshot_exposes_restored_may_2026_values(monkeypatch):
    monkeypatch.setattr(report, "is_pro", lambda _telegram_id: True)
    for module in (config, db_manager, report, telegram_bot, legacy_bot):
        monkeypatch.setattr(module, "DB_NAME", LIVE_DB, raising=False)
    snapshot = build_unified_financial_snapshot_dict(TEST_USER_ID, TEST_DAYS, bot=telegram_bot)

    assert snapshot["revenue"] == 1_067_554.02
    assert snapshot["wb_payout"] == 768_149.08
    assert snapshot["payments_received"] == 480_472.04
    assert snapshot["cost_price"] == 276_532.00
    assert snapshot["advertising"] == 110_449.92
    assert snapshot["logistics"] == 123_743.24
    assert snapshot["storage"] == 2_686.72
    assert snapshot["acquiring"] == 17_727.09
    assert snapshot["wb_deductions"] == 76_736.00
    assert snapshot["other_expenses"] == 97_317.61
    assert snapshot["unclassified_expenses"] == 2_854.52
    assert snapshot["profit_before_tax"] == 359_506.92
    assert snapshot["profit"] == 359_506.92
    assert snapshot["margin"] == 33.7
    assert snapshot["roi"] == 92.9
