from __future__ import annotations

from contextlib import redirect_stdout
import importlib
import io
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_modules(tmp_path, *, wb_token=""):
    os.environ["DB_DIR"] = str(tmp_path)
    os.environ["VOOGLII_TOKEN_ENCRYPTION_KEY"] = "test-encryption-key-1234567890-abcdef"
    os.environ["WB_TOKEN"] = wb_token

    import config
    import db_manager
    import user_manager
    import vooglii_telegram.services.token_resolver as token_resolver

    importlib.reload(config)
    importlib.reload(db_manager)
    importlib.reload(user_manager)
    importlib.reload(token_resolver)
    return config, db_manager, user_manager, token_resolver


def test_encrypted_token_is_resolved_from_users(tmp_path):
    _config, _db_manager, user_manager, token_resolver = _reload_modules(tmp_path)
    raw_token = "abcdefghijklmnopqrstuvwxyz123456"
    user_manager.save_user(123456, "token_user", raw_token)

    resolution = token_resolver.resolve_wb_token(123456)

    assert resolution.status == "SUCCESS"
    assert resolution.token == raw_token
    assert resolution.source == "users_encrypted"
    assert resolution.encrypted is True
    assert resolution.token_len == len(raw_token)


def test_missing_token_returns_no_token(tmp_path):
    _config, _db_manager, user_manager, token_resolver = _reload_modules(tmp_path)
    user_manager.ensure_user(777, "missing_user")

    resolution = token_resolver.resolve_wb_token(777)

    assert resolution.status == "NO_TOKEN"
    assert resolution.token is None
    assert resolution.source == "missing"


def test_check_wb_token_resolution_never_prints_token(tmp_path):
    _config, _db_manager, user_manager, _token_resolver = _reload_modules(tmp_path)
    raw_token = "abcdefghijklmnopqrstuvwxyz123456"
    user_manager.save_user(222, "script_user", raw_token)

    import scripts.check_wb_token_resolution as check_script

    old_argv = sys.argv
    stdout = io.StringIO()
    try:
        sys.argv = ["check_wb_token_resolution.py", "--user-id", "222"]
        with redirect_stdout(stdout):
            check_script.main()
    finally:
        sys.argv = old_argv

    output = stdout.getvalue()
    assert "token_source: users_encrypted" in output
    assert f"token_len: {len(raw_token)}" in output
    assert raw_token not in output


def test_backfill_uses_token_resolver(monkeypatch):
    import scripts.backfill_financial_period as backfill_script
    from vooglii_telegram.services.token_resolver import TokenResolution

    monkeypatch.setattr(
        backfill_script,
        "resolve_wb_token",
        lambda _user_id: TokenResolution(token=None, source="missing", encrypted=False, reason="no token source available"),
    )
    monkeypatch.setattr(
        backfill_script,
        "get_user",
        lambda user_id: (user_id, "Andrusha_rzn", None, "PRO", 1, None, None, "owner", "2026-08-09", None, None),
    )

    result = backfill_script._run_backfill(658486226, "2026-05-01", "2026-05-31", "wb-api")

    token_block = (result.get("api_blocks") or {}).get("token") or {}
    assert token_block.get("status") == "WB_API_UNAVAILABLE_FOR_PERIOD:NO_TOKEN"
    assert token_block.get("token_source") == "missing"
