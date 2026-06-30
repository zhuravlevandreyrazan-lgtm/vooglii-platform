"""Regression checks for readonly runtime write guards.

Run with:
    python tests/readonly_runtime_guard.py
"""

from pathlib import Path
import asyncio
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import db_manager
import load_sales
import telegram_bot
import user_manager

TEST_USER_ID = 658486226
TEST_DAYS = ("2026-05-01", "2026-05-31")


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


class _ReadonlyCursor:
    def __init__(self):
        self._last_sql = ""

    def execute(self, sql, params=()):
        self._last_sql = str(sql or "")
        normalized = self._last_sql.strip().upper()
        if normalized.startswith("SELECT"):
            return self
        if normalized.startswith("PRAGMA"):
            return self
        raise sqlite3.OperationalError("attempt to write a readonly database")

    def fetchone(self):
        if "SELECT TELEGRAM_ID FROM USERS" in self._last_sql.upper():
            return None
        return None

    def fetchall(self):
        return []


class _ReadonlyConn:
    def cursor(self):
        return _ReadonlyCursor()

    def execute(self, sql, params=()):
        return self.cursor().execute(sql, params)

    def commit(self):
        return None

    def close(self):
        return None


class _DummyMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(str(text))


class _DummyUser:
    id = TEST_USER_ID
    username = "readonly-test"


class _DummyUpdate:
    def __init__(self):
        self.effective_user = _DummyUser()
        self.message = _DummyMessage()


def test_is_readonly_db_error():
    exc = sqlite3.OperationalError("attempt to write a readonly database")
    _assert(telegram_bot._is_readonly_db_error(exc), "_is_readonly_db_error should detect readonly sqlite error")


def test_optional_user_write_skipped():
    original_conn = user_manager._conn
    try:
        user_manager._conn = lambda: _ReadonlyConn()
        result = user_manager.ensure_user(TEST_USER_ID, "readonly-test")
        _assert(result is False, "ensure_user should skip optional write on readonly DB")
    finally:
        user_manager._conn = original_conn


def test_optional_sync_status_write_skipped():
    original_init_db = load_sales.init_db
    original_connect = load_sales.sqlite3.connect
    try:
        load_sales.init_db = lambda: None
        load_sales.sqlite3.connect = lambda *args, **kwargs: _ReadonlyConn()
        load_sales.ensure_sync_status_rows(TEST_USER_ID)
    finally:
        load_sales.init_db = original_init_db
        load_sales.sqlite3.connect = original_connect


def test_access_and_cfo_insights_readonly_safe():
    update = _DummyUpdate()
    allowed = asyncio.run(telegram_bot.access(update, "report"))
    _assert(allowed is True, "access(report) should not require a DB write")
    text = telegram_bot._cfo_insights_text(TEST_USER_ID, TEST_DAYS)
    _assert(isinstance(text, str) and "VOOGLII CFO" in text, "cfo insights text should still be generated")


def test_init_db_schema_bootstrap_skipped_in_readonly_mode():
    original_get_conn = db_manager.get_conn
    try:
        db_manager.get_conn = lambda: _ReadonlyConn()
        db_manager.init_db()
    finally:
        db_manager.get_conn = original_get_conn


def run_all():
    test_is_readonly_db_error()
    test_optional_user_write_skipped()
    test_optional_sync_status_write_skipped()
    test_access_and_cfo_insights_readonly_safe()
    test_init_db_schema_bootstrap_skipped_in_readonly_mode()


if __name__ == "__main__":
    run_all()
    print("READONLY RUNTIME GUARD OK")
