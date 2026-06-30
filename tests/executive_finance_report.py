"""Readonly regression test for executive finance report layout."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _index_of(lines, needle):
    for index, line in enumerate(lines):
        if str(line).strip() == needle:
            return index
    return -1


def main():
    original_profit_audit_snapshot = telegram_bot._profit_audit_snapshot
    try:
        base_snapshot = original_profit_audit_snapshot(658486226, ("2026-05-01", "2026-05-31"))

        def _fake_profit_audit_snapshot(user, days, context=None):
            snapshot = dict(base_snapshot)
            payout_verification_debug = dict(snapshot.get("payout_verification_debug") or {})
            finance_explainability = dict(snapshot.get("finance_explainability") or {})
            snapshot["reconciliation_status"] = "OVEREXPLAINED"
            payout_verification_debug["status"] = "DEGRADED"
            payout_verification_debug["reconciliation_status"] = "OVEREXPLAINED"
            finance_explainability["status"] = "OVEREXPLAINED"
            snapshot["payout_verification_debug"] = payout_verification_debug
            snapshot["finance_explainability"] = finance_explainability
            return snapshot

        telegram_bot._profit_audit_snapshot = _fake_profit_audit_snapshot
        text = telegram_bot._profit_audit_text("custom", ("2026-05-01", "2026-05-31"), 658486226)
    finally:
        telegram_bot._profit_audit_snapshot = original_profit_audit_snapshot

    lines = [line.strip() for line in text.splitlines()]

    required_blocks = [
        "УПРАВЛЕНЧЕСКАЯ СВОДКА",
        "ГЛАВНЫЕ ВЫВОДЫ",
        "РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ",
        "КЛЮЧЕВЫЕ ФИНАНСОВЫЕ ПОКАЗАТЕЛИ",
        "ФИНАНСОВАЯ ДЕТАЛИЗАЦИЯ",
        "FINANCE EXPLAINABILITY",
        "УПРАВЛЕНЧЕСКИЙ ВЕРДИКТ",
        "PROFIT RECONCILIATION",
        "WB PAYOUT BRIDGE",
        "PROFIT MODEL STATUS",
        "WARNINGS",
        "FINANCE DEBUG",
    ]
    for block in required_blocks:
        _assert(block in lines, f"missing block {block}")

    ordered_blocks = [
        "УПРАВЛЕНЧЕСКАЯ СВОДКА",
        "ГЛАВНЫЕ ВЫВОДЫ",
        "РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ",
        "КЛЮЧЕВЫЕ ФИНАНСОВЫЕ ПОКАЗАТЕЛИ",
        "ФИНАНСОВАЯ ДЕТАЛИЗАЦИЯ",
        "FINANCE EXPLAINABILITY",
        "УПРАВЛЕНЧЕСКИЙ ВЕРДИКТ",
        "PROFIT RECONCILIATION",
        "WB PAYOUT BRIDGE",
        "PROFIT MODEL STATUS",
        "WARNINGS",
        "FINANCE DEBUG",
    ]
    indexes = [_index_of(lines, item) for item in ordered_blocks]
    _assert(all(index >= 0 for index in indexes), "all ordered blocks must exist")
    _assert(indexes == sorted(indexes), "blocks are out of order")
    _assert(_index_of(lines, "УПРАВЛЕНЧЕСКИЙ ВЕРДИКТ") < _index_of(lines, "WARNINGS"), "executive verdict should be above warnings")

    executive_window = "\n".join(lines[:40])
    for marker in ("Операционная прибыль", "Доверие к расчёту", "Уверенность", "Статус бизнеса"):
        _assert(marker in executive_window, f"executive window missing {marker}")

    _assert("1." in text, "recommended actions should be numbered")
    _assert("Официальная прибыль" in text, "executive summary should include official profit")
    _assert("Recommended action:" in text, "finance explainability should include recommended action")
    _assert("OVEREXPLAINED" in text, "overexplained status should be preserved")
    _assert("DEGRADED" in text, "degraded status should be preserved")
    _assert(lines.count("ФИНАНСЫ") == 0, "generic duplicate finance header should not remain")

    for index in range(len(lines) - 1):
        left = lines[index]
        right = lines[index + 1]
        if left and right and left == right and left in (
            "УПРАВЛЕНЧЕСКАЯ СВОДКА",
            "ГЛАВНЫЕ ВЫВОДЫ",
            "РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ",
            "УПРАВЛЕНЧЕСКИЙ ВЕРДИКТ",
        ):
            raise AssertionError("duplicate executive block headers detected")

    print("EXECUTIVE FINANCE REPORT TEST OK")


if __name__ == "__main__":
    main()
