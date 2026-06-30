"""Readonly RC stability checks."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import telegram_bot

TEST_USER_ID = 658486226
TEST_DAYS = ("2026-05-01", "2026-05-31")


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def run_all():
    snapshot = telegram_bot._rc_stability_snapshot(TEST_USER_ID, TEST_DAYS)
    _assert(isinstance(snapshot, dict), "rc stability snapshot should be dict")
    _assert(str(snapshot.get("status") or "") in telegram_bot.RC_STABILITY_ALLOWED_STATUS, "rc stability status out of allowed set")
    _assert(isinstance(snapshot.get("tested_commands"), list), "tested_commands should be list")
    _assert(isinstance(snapshot.get("command_latency"), dict), "command_latency should be dict")
    _assert("director" in (snapshot.get("command_latency") or {}), "command_latency should include director")
    _assert(isinstance(snapshot.get("request_context_isolated"), bool), "request_context_isolated should be bool")
    _assert(snapshot.get("memory_delta_mb") is not None, "memory_delta_mb should exist")
    _assert(str(snapshot.get("scheduler_status") or "") in telegram_bot.RC_STABILITY_ALLOWED_SCHEDULER_STATUS, "scheduler_status out of allowed set")
    _assert(str(snapshot.get("telegram_runtime_status") or "") in telegram_bot.RC_STABILITY_ALLOWED_RUNTIME_STATUS, "telegram_runtime_status out of allowed set")
    _assert(isinstance(snapshot.get("warnings"), list), "warnings should be list")
    _assert(isinstance(snapshot.get("recommendations"), list), "recommendations should be list")

    text = telegram_bot._rc_status_text(TEST_USER_ID, TEST_DAYS)
    _assert(isinstance(text, str), "rc status text should be str")
    _assert("RELEASE CANDIDATE STATUS" in text, "rc status text missing title")

    print("RC STABILITY OK")


if __name__ == "__main__":
    run_all()
