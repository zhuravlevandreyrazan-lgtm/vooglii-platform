from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Iterable

from config import DB_NAME, WB_TOKEN
from db_manager import init_db
from security.token_crypto import decrypt_token, is_encrypted_token, validate_wb_token


@dataclass
class TokenResolution:
    token: str | None
    source: str
    encrypted: bool
    reason: str | None = None

    @property
    def token_len(self) -> int:
        return len(str(self.token or ""))

    @property
    def can_decrypt(self) -> bool:
        return bool(self.token)

    @property
    def status(self) -> str:
        return "SUCCESS" if self.token else "NO_TOKEN"


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_token(raw_value: str | None, source: str) -> TokenResolution:
    value = str(raw_value or "").strip()
    if not value:
        return TokenResolution(token=None, source=source, encrypted=False, reason="empty_value")
    encrypted = is_encrypted_token(value)
    try:
        token = decrypt_token(value) if encrypted else validate_wb_token(value)
    except Exception as exc:
        return TokenResolution(token=None, source=source, encrypted=encrypted, reason=f"{type(exc).__name__}")
    return TokenResolution(token=token, source=source, encrypted=encrypted, reason=None)


def _resolve_from_users(conn: sqlite3.Connection, user_id: int) -> TokenResolution:
    row = conn.execute("SELECT wb_token FROM users WHERE telegram_id=?", (user_id,)).fetchone()
    if not row:
        return TokenResolution(token=None, source="users_plain", encrypted=False, reason="user_not_found")
    value = str(row["wb_token"] or "").strip()
    if not value:
        return TokenResolution(token=None, source="users_plain", encrypted=False, reason="users.wb_token empty")
    resolution = _normalize_token(value, "users_encrypted" if is_encrypted_token(value) else "users_plain")
    if resolution.token:
        return resolution
    return TokenResolution(token=None, source=resolution.source, encrypted=resolution.encrypted, reason=resolution.reason)


def _resolve_from_wb_cabinets(conn: sqlite3.Connection, user_id: int) -> TokenResolution:
    try:
        row = conn.execute(
            """
            SELECT seller_token_encrypted, statistics_token_encrypted, advertising_token_encrypted, finance_token_encrypted
            FROM wb_cabinets
            WHERE data_owner_id=?
            ORDER BY connected DESC, updated_at DESC, created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return TokenResolution(token=None, source="wb_cabinets", encrypted=False, reason="wb_cabinets unavailable")
    if not row:
        return TokenResolution(token=None, source="wb_cabinets", encrypted=False, reason="cabinet_not_found")
    for column in (
        "statistics_token_encrypted",
        "seller_token_encrypted",
        "advertising_token_encrypted",
        "finance_token_encrypted",
    ):
        value = str(row[column] or "").strip()
        if not value:
            continue
        resolution = _normalize_token(value, "wb_cabinets")
        if resolution.token:
            return resolution
        return TokenResolution(token=None, source="wb_cabinets", encrypted=resolution.encrypted, reason=resolution.reason)
    return TokenResolution(token=None, source="wb_cabinets", encrypted=False, reason="cabinet_tokens_empty")


def _resolve_from_config() -> TokenResolution:
    value = str(WB_TOKEN or "").strip()
    if not value:
        return TokenResolution(token=None, source="config", encrypted=False, reason="config.WB_TOKEN empty")
    resolution = _normalize_token(value, "config")
    if resolution.token:
        return resolution
    return TokenResolution(token=None, source="config", encrypted=resolution.encrypted, reason=resolution.reason)


def resolve_wb_token(user_id: int) -> TokenResolution:
    conn = _connect()
    try:
        for resolution in (
            _resolve_from_users(conn, user_id),
            _resolve_from_wb_cabinets(conn, user_id),
            _resolve_from_config(),
        ):
            if resolution.token:
                return resolution
        return TokenResolution(token=None, source="missing", encrypted=False, reason="no token source available")
    finally:
        conn.close()


def resolve_active_wb_tokens(user_id: int | None = None) -> list[tuple[int, str]]:
    conn = _connect()
    try:
        today_rowset: Iterable[sqlite3.Row] = conn.execute(
            """
            SELECT telegram_id
            FROM users
            WHERE is_active=1
              AND (
                  UPPER(COALESCE(tariff,'FREE'))!='PRO'
                  OR subscription_until IS NULL
                  OR subscription_until=''
                  OR subscription_until>=date('now')
              )
              AND (? IS NULL OR telegram_id=?)
            ORDER BY telegram_id
            """,
            (user_id, user_id),
        ).fetchall()
        resolved: list[tuple[int, str]] = []
        for row in today_rowset:
            resolved_token = resolve_wb_token(int(row["telegram_id"]))
            if resolved_token.token:
                resolved.append((int(row["telegram_id"]), resolved_token.token))
        return resolved
    finally:
        conn.close()
