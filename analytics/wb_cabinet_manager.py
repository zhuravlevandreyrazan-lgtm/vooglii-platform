from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from analytics.cache import invalidate_cache
from analytics.common import DEFAULT_USER_ID
from analytics.logging_config import get_logger
from config import BOT_TOKEN, DB_NAME, WB_CABINET_SECRET, WB_TOKEN
from db_manager import get_conn, init_db
from load_sales import (
    ads_probe,
    backfill_advertising_period,
    backfill_sales_orders_range,
    inspect_orders_api,
    inspect_sales_api,
    load_finance_expenses,
    load_stocks,
)
from telegram_bot import fetch_wb_finance_reports_list


LOGGER = get_logger("wb_cabinet_manager")
WORKSPACE_CACHE_KEYS = [
    "executive",
    "business",
    "finance",
    "advertising",
    "products",
    "inventory",
    "advisor",
    "decision_engine",
    "forecast",
    "reports",
    "system",
]
HEALTH_SECTIONS = ("seller", "statistics", "advertising", "finance")
SYNC_TYPES = ("sales", "orders", "products", "cards", "stocks", "advertising", "finance", "all")
LEGACY_ORG_ALIASES = {
    "org_vooglii_demo": "org_vooglii_main",
    "org_test_seller": "org_vooglii_main",
    "org_agency_demo": "org_vooglii_main",
}
LEGACY_CABINET_ALIASES = {
    "cabinet_vooglii_main": "wb_cabinet_unconfigured",
    "cabinet_test_fashion": "wb_cabinet_unconfigured",
    "cabinet_vooglii_home": "wb_cabinet_unconfigured",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _secret_key() -> bytes:
    seed = WB_CABINET_SECRET or BOT_TOKEN or WB_TOKEN or DB_NAME or "vooglii-wb-cabinet"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _encrypt_token(token: str | None) -> str | None:
    raw = str(token or "").strip()
    if not raw:
        return None
    key = _secret_key()
    payload = bytes(ord(char) ^ key[index % len(key)] for index, char in enumerate(raw))
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decrypt_token(token: str | None) -> str | None:
    raw = str(token or "").strip()
    if not raw:
        return None
    try:
        data = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception:
        return None
    key = _secret_key()
    return "".join(chr(byte ^ key[index % len(key)]) for index, byte in enumerate(data))


def _mask_token(token: str | None) -> str | None:
    raw = str(token or "").strip()
    if not raw:
        return None
    if len(raw) <= 8:
        return "*" * len(raw)
    return f"{raw[:4]}...{raw[-4:]}"


def _parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def invalidate_workspace_caches() -> None:
    for key in WORKSPACE_CACHE_KEYS:
        invalidate_cache(key)


def _db_conn():
    init_db()
    return get_conn()


def _row_to_org(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "plan": str(row["plan"] or "starter"),
        "status": str(row["status"] or "active"),
        "createdAt": row["created_at"],
        "health": "Healthy",
    }


def _health_from_status(status: str, connected: bool, data_quality: str) -> str:
    if not connected:
        return "Watch"
    if status in {"error", "failed"}:
        return "Critical"
    if str(data_quality or "").lower() in {"high", "good"}:
        return "Healthy"
    return "Watch"


def _token_status_from_row(row: sqlite3.Row) -> str:
    masks = [
        row["seller_token_masked"],
        row["statistics_token_masked"],
        row["advertising_token_masked"],
        row["finance_token_masked"],
    ]
    filled = sum(1 for item in masks if item)
    if filled == 0:
        return "not_configured"
    if filled < len(masks):
        return "partial"
    return "configured"


def _row_to_cabinet(row: sqlite3.Row | None, organization_name: str | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    scopes = _parse_json(row["scopes"], [])
    connected = bool(row["connected"])
    data_quality = str(row["data_quality"] or "pending")
    status = str(row["status"] or ("connected" if connected else "disconnected"))
    return {
        "id": str(row["id"]),
        "organizationId": str(row["organization_id"]),
        "organizationName": organization_name,
        "name": str(row["name"]),
        "sellerId": str(row["seller_id"] or ""),
        "status": status,
        "connected": connected,
        "lastSyncAt": row["last_sync_at"],
        "dataQuality": data_quality,
        "tokenStatus": _token_status_from_row(row),
        "health": _health_from_status(status, connected, data_quality),
        "lastSyncStatus": row["last_sync_status"],
        "syncMessage": row["sync_message"],
        "lastCheckedAt": row["last_checked_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "scopes": scopes if isinstance(scopes, list) else [],
        "tokens": {
            "seller": row["seller_token_masked"],
            "statistics": row["statistics_token_masked"],
            "advertising": row["advertising_token_masked"],
            "finance": row["finance_token_masked"],
        },
        "dataOwnerId": int(row["data_owner_id"]),
    }


def _virtual_cabinet() -> dict[str, Any]:
    return {
        "id": "wb_cabinet_unconfigured",
        "organizationId": "org_vooglii_main",
        "organizationName": "VOOGLII Workspace",
        "name": "Кабинет Wildberries не подключен",
        "sellerId": "",
        "status": "disconnected",
        "connected": False,
        "lastSyncAt": None,
        "dataQuality": "pending",
        "tokenStatus": "not_configured",
        "health": "Watch",
        "lastSyncStatus": None,
        "syncMessage": "Добавьте кабинет и выполните первую синхронизацию.",
        "lastCheckedAt": None,
        "createdAt": _iso_now(),
        "updatedAt": _iso_now(),
        "scopes": [],
        "tokens": {"seller": None, "statistics": None, "advertising": None, "finance": None},
        "dataOwnerId": DEFAULT_USER_ID,
    }


def _virtual_legacy_cabinet(cabinet_id: str) -> dict[str, Any]:
    cabinet = _virtual_cabinet()
    cabinet["id"] = cabinet_id
    cabinet["name"] = "Legacy compatibility cabinet"
    return cabinet


def _ensure_workspace_state(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        INSERT OR IGNORE INTO workspace_state(state_key, organization_id, cabinet_id, last_changed)
        VALUES('active', 'org_vooglii_main', NULL, ?)
        """,
        (_iso_now(),),
    )


def _next_data_owner_id(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT COUNT(*) FROM wb_cabinets")
    cabinets_count = int((cur.fetchone() or [0])[0] or 0)
    if cabinets_count == 0:
        return DEFAULT_USER_ID
    cur.execute("SELECT MAX(data_owner_id) FROM wb_cabinets")
    max_cabinet_owner = int((cur.fetchone() or [0])[0] or 0)
    cur.execute("SELECT MAX(COALESCE(telegram_id, 0)) FROM users")
    max_user_owner = int((cur.fetchone() or [0])[0] or 0)
    return max(DEFAULT_USER_ID, max_cabinet_owner, max_user_owner) + 1


def list_organizations() -> list[dict[str, Any]]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        _ensure_workspace_state(cur)
        cur.execute(
            """
            SELECT o.*,
                   COUNT(c.id) AS cabinet_count
            FROM organizations o
            LEFT JOIN wb_cabinets c ON c.organization_id = o.id
            GROUP BY o.id
            ORDER BY o.created_at ASC, o.id ASC
            """
        )
        rows = []
        for row in cur.fetchall():
            item = _row_to_org(row) or {}
            item["cabinetCount"] = int(row["cabinet_count"] or 0)
            rows.append(item)
        return rows


def get_organization(organization_id: str) -> dict[str, Any]:
    resolved_id = LEGACY_ORG_ALIASES.get(organization_id, organization_id)
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM organizations WHERE id = ?", (resolved_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(organization_id)
        cur.execute("SELECT COUNT(*) FROM wb_cabinets WHERE organization_id = ?", (resolved_id,))
        org = _row_to_org(row) or {}
        if organization_id != resolved_id:
            org["id"] = organization_id
        org["cabinetCount"] = int((cur.fetchone() or [0])[0] or 0)
        return org


def list_cabinets(organization_id: str | None = None) -> list[dict[str, Any]]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        query = """
            SELECT c.*, o.name AS organization_name
            FROM wb_cabinets c
            JOIN organizations o ON o.id = c.organization_id
        """
        params: list[Any] = []
        if organization_id:
            query += " WHERE c.organization_id = ?"
            params.append(organization_id)
        query += " ORDER BY c.updated_at DESC, c.created_at DESC, c.id DESC"
        cur.execute(query, tuple(params))
        return [
            _row_to_cabinet(row, organization_name=row["organization_name"])
            for row in cur.fetchall()
        ]


def get_cabinet(cabinet_id: str, *, allow_virtual: bool = False) -> dict[str, Any]:
    resolved_id = LEGACY_CABINET_ALIASES.get(cabinet_id, cabinet_id)
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.*, o.name AS organization_name
            FROM wb_cabinets c
            JOIN organizations o ON o.id = c.organization_id
            WHERE c.id = ?
            """,
            (resolved_id,),
        )
        row = cur.fetchone()
        if row is not None:
            cabinet = _row_to_cabinet(row, organization_name=row["organization_name"]) or _virtual_cabinet()
            if cabinet_id != resolved_id:
                cabinet["id"] = cabinet_id
            return cabinet
    if allow_virtual or cabinet_id in LEGACY_CABINET_ALIASES:
        if cabinet_id in LEGACY_CABINET_ALIASES:
            return _virtual_legacy_cabinet(cabinet_id)
        return _virtual_cabinet()
    raise KeyError(cabinet_id)


def get_active_workspace_state() -> dict[str, Any]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        _ensure_workspace_state(cur)
        cur.execute("SELECT * FROM workspace_state WHERE state_key = 'active'")
        row = cur.fetchone()
        return {
            "organizationId": row["organization_id"] if row else "org_vooglii_main",
            "cabinetId": row["cabinet_id"] if row else None,
            "lastChanged": row["last_changed"] if row else _iso_now(),
        }


def get_active_organization() -> dict[str, Any]:
    state = get_active_workspace_state()
    organization_id = str(state.get("organizationId") or "org_vooglii_main")
    return get_organization(organization_id)


def get_active_cabinet() -> dict[str, Any]:
    state = get_active_workspace_state()
    cabinet_id = state.get("cabinetId")
    if cabinet_id:
        try:
            return get_cabinet(str(cabinet_id))
        except KeyError:
            pass
    cabinets = list_cabinets(str(state.get("organizationId") or "org_vooglii_main"))
    if cabinets:
        return cabinets[0]
    return _virtual_cabinet()


def get_active_cabinet_user_id() -> int:
    cabinet = get_active_cabinet()
    return int(cabinet.get("dataOwnerId") or DEFAULT_USER_ID)


def get_workspace_context(mode: str = "live") -> dict[str, Any]:
    state = get_active_workspace_state()
    organizations = list_organizations()
    organization = get_active_organization()
    cabinet = get_active_cabinet()
    return {
        "organizationId": organization["id"],
        "cabinetId": cabinet["id"] if cabinet["id"] != "wb_cabinet_unconfigured" else None,
        "mode": mode,
        "lastChanged": state["lastChanged"],
        "organizationCount": len(organizations),
        "cabinetCount": len(list_cabinets(str(organization["id"]))),
        "organization": organization,
        "cabinet": cabinet,
    }


def _set_workspace_state(cur: sqlite3.Cursor, *, organization_id: str, cabinet_id: str | None) -> None:
    cur.execute(
        """
        INSERT INTO workspace_state(state_key, organization_id, cabinet_id, last_changed)
        VALUES('active', ?, ?, ?)
        ON CONFLICT(state_key) DO UPDATE SET
            organization_id = excluded.organization_id,
            cabinet_id = excluded.cabinet_id,
            last_changed = excluded.last_changed
        """,
        (organization_id, cabinet_id, _iso_now()),
    )


def select_organization(organization_id: str) -> dict[str, Any]:
    organization = get_organization(organization_id)
    resolved_id = LEGACY_ORG_ALIASES.get(organization_id, organization_id)
    cabinets = list_cabinets(resolved_id)
    cabinet_id = cabinets[0]["id"] if cabinets else "cabinet_vooglii_main"
    with _db_conn() as conn:
        cur = conn.cursor()
        _set_workspace_state(cur, organization_id=resolved_id, cabinet_id=cabinet_id)
        conn.commit()
    invalidate_workspace_caches()
    return get_workspace_context(mode="live")


def select_cabinet(cabinet_id: str) -> dict[str, Any]:
    cabinet = get_cabinet(cabinet_id)
    resolved_org = LEGACY_ORG_ALIASES.get(str(cabinet["organizationId"]), str(cabinet["organizationId"]))
    with _db_conn() as conn:
        cur = conn.cursor()
        _set_workspace_state(cur, organization_id=resolved_org, cabinet_id=str(cabinet["id"]))
        conn.commit()
    invalidate_workspace_caches()
    return get_workspace_context(mode="live")


def _scoped_row(record: dict[str, Any], mode: str = "live") -> dict[str, Any]:
    context = get_workspace_context(mode=mode)
    scoped = dict(record)
    scoped["organizationId"] = context["organizationId"]
    scoped["organizationName"] = (context.get("organization") or {}).get("name")
    scoped["cabinetId"] = context.get("cabinetId")
    scoped["cabinetName"] = (context.get("cabinet") or {}).get("name")
    scoped["workspaceMode"] = context["mode"]
    return scoped


def scoped_record(record: dict[str, Any], mode: str = "live") -> dict[str, Any]:
    return _scoped_row(record, mode=mode)


def scoped_records(records: list[dict[str, Any]], mode: str = "live") -> list[dict[str, Any]]:
    return [_scoped_row(record, mode=mode) for record in records]


def _clean_scope_list(payload: list[str] | None) -> list[str]:
    scopes = []
    for item in payload or []:
        value = str(item or "").strip().lower()
        if value and value not in scopes:
            scopes.append(value)
    return scopes


def _cabinet_payload_to_row(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    current = existing or {}
    name = str(payload.get("name") or current.get("name") or "").strip()
    if not name:
        raise ValueError("Cabinet name is required.")
    organization_id = str(payload.get("organizationId") or current.get("organizationId") or "org_vooglii_main")
    seller_id = str(payload.get("sellerId") or current.get("sellerId") or "").strip() or None
    scopes = _clean_scope_list(payload.get("scopes") or current.get("scopes") or [])
    tokens = dict(current.get("tokens") or {})
    token_patch = payload.get("tokens") or {}
    if isinstance(token_patch, dict):
        for key in ("seller", "statistics", "advertising", "finance"):
            candidate = token_patch.get(key)
            if candidate is not None:
                tokens[key] = str(candidate).strip() or None
    connected = bool(current.get("connected")) and bool(tokens)
    return {
        "organization_id": organization_id,
        "name": name,
        "seller_id": seller_id,
        "scopes": scopes,
        "tokens": tokens,
        "connected": connected,
    }


def create_cabinet(payload: dict[str, Any]) -> dict[str, Any]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        normalized = _cabinet_payload_to_row(payload)
        cabinet_id = str(payload.get("id") or f"cab_{uuid4().hex[:12]}")
        data_owner_id = _next_data_owner_id(cur)
        now = _iso_now()
        cur.execute(
            """
            INSERT INTO wb_cabinets(
                id, organization_id, data_owner_id, name, seller_id,
                seller_token_encrypted, seller_token_masked,
                statistics_token_encrypted, statistics_token_masked,
                advertising_token_encrypted, advertising_token_masked,
                finance_token_encrypted, finance_token_masked,
                status, scopes, connected, data_quality, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cabinet_id,
                normalized["organization_id"],
                data_owner_id,
                normalized["name"],
                normalized["seller_id"],
                _encrypt_token(normalized["tokens"].get("seller")),
                _mask_token(normalized["tokens"].get("seller")),
                _encrypt_token(normalized["tokens"].get("statistics")),
                _mask_token(normalized["tokens"].get("statistics")),
                _encrypt_token(normalized["tokens"].get("advertising")),
                _mask_token(normalized["tokens"].get("advertising")),
                _encrypt_token(normalized["tokens"].get("finance")),
                _mask_token(normalized["tokens"].get("finance")),
                "connected" if normalized["connected"] else "disconnected",
                _serialize_json(normalized["scopes"]),
                1 if normalized["connected"] else 0,
                "pending",
                now,
                now,
            ),
        )
        cur.execute(
            "SELECT cabinet_id FROM workspace_state WHERE state_key = 'active'"
        )
        active_cabinet = (cur.fetchone() or [None])[0]
        if not active_cabinet:
            _set_workspace_state(cur, organization_id=normalized["organization_id"], cabinet_id=cabinet_id)
        conn.commit()
    invalidate_workspace_caches()
    return get_cabinet(cabinet_id)


def update_cabinet(cabinet_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = get_cabinet(cabinet_id)
    normalized = _cabinet_payload_to_row(payload, existing=existing)
    now = _iso_now()
    with _db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE wb_cabinets
            SET organization_id = ?,
                name = ?,
                seller_id = ?,
                seller_token_encrypted = COALESCE(?, seller_token_encrypted),
                seller_token_masked = COALESCE(?, seller_token_masked),
                statistics_token_encrypted = COALESCE(?, statistics_token_encrypted),
                statistics_token_masked = COALESCE(?, statistics_token_masked),
                advertising_token_encrypted = COALESCE(?, advertising_token_encrypted),
                advertising_token_masked = COALESCE(?, advertising_token_masked),
                finance_token_encrypted = COALESCE(?, finance_token_encrypted),
                finance_token_masked = COALESCE(?, finance_token_masked),
                scopes = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                normalized["organization_id"],
                normalized["name"],
                normalized["seller_id"],
                _encrypt_token(normalized["tokens"].get("seller")),
                _mask_token(normalized["tokens"].get("seller")),
                _encrypt_token(normalized["tokens"].get("statistics")),
                _mask_token(normalized["tokens"].get("statistics")),
                _encrypt_token(normalized["tokens"].get("advertising")),
                _mask_token(normalized["tokens"].get("advertising")),
                _encrypt_token(normalized["tokens"].get("finance")),
                _mask_token(normalized["tokens"].get("finance")),
                _serialize_json(normalized["scopes"]),
                now,
                cabinet_id,
            ),
        )
        if "connected" in payload:
            connected = bool(payload.get("connected"))
            cur.execute(
                "UPDATE wb_cabinets SET connected = ?, status = ?, updated_at = ? WHERE id = ?",
                (1 if connected else 0, "connected" if connected else "disconnected", now, cabinet_id),
            )
        conn.commit()
    invalidate_workspace_caches()
    return get_cabinet(cabinet_id)


def delete_cabinet(cabinet_id: str) -> dict[str, Any]:
    cabinet = get_cabinet(cabinet_id)
    with _db_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM wb_api_health WHERE cabinet_id = ?", (cabinet_id,))
        cur.execute("DELETE FROM wb_sync_jobs WHERE cabinet_id = ?", (cabinet_id,))
        cur.execute("DELETE FROM wb_cabinets WHERE id = ?", (cabinet_id,))
        cur.execute("SELECT organization_id, cabinet_id FROM workspace_state WHERE state_key = 'active'")
        row = cur.fetchone()
        if row and row[1] == cabinet_id:
            remaining = list_cabinets(row[0])
            next_cabinet = remaining[0]["id"] if remaining else None
            _set_workspace_state(cur, organization_id=row[0], cabinet_id=next_cabinet)
        conn.commit()
    invalidate_workspace_caches()
    deleted = dict(cabinet)
    deleted["status"] = "deleted"
    deleted["connected"] = False
    return deleted


def _load_cabinet_tokens(cabinet_id: str) -> dict[str, str | None]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT seller_token_encrypted, statistics_token_encrypted,
                   advertising_token_encrypted, finance_token_encrypted
            FROM wb_cabinets
            WHERE id = ?
            """,
            (cabinet_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise KeyError(cabinet_id)
        return {
            "seller": _decrypt_token(row["seller_token_encrypted"]),
            "statistics": _decrypt_token(row["statistics_token_encrypted"]),
            "advertising": _decrypt_token(row["advertising_token_encrypted"]),
            "finance": _decrypt_token(row["finance_token_encrypted"]),
        }


def _set_health(cabinet_id: str, section: str, status: str, *, message: str | None = None, error: str | None = None) -> None:
    now = _iso_now()
    with _db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO wb_api_health(
                cabinet_id, section, status, last_success_at, last_error_at,
                last_error_message, rate_limit_state, message, required_action
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cabinet_id, section) DO UPDATE SET
                status = excluded.status,
                last_success_at = CASE
                    WHEN excluded.status IN ('ok', 'connected', 'healthy', 'partial') THEN excluded.last_success_at
                    ELSE wb_api_health.last_success_at
                END,
                last_error_at = CASE
                    WHEN excluded.status IN ('error', 'failed', 'missing_token') THEN excluded.last_error_at
                    ELSE wb_api_health.last_error_at
                END,
                last_error_message = excluded.last_error_message,
                rate_limit_state = excluded.rate_limit_state,
                message = excluded.message,
                required_action = excluded.required_action
            """,
            (
                cabinet_id,
                section,
                status,
                now if status in {"ok", "connected", "healthy", "partial"} else None,
                now if status in {"error", "failed", "missing_token"} else None,
                error,
                None,
                message,
                "Добавьте корректный токен." if status == "missing_token" else None,
            ),
        )
        conn.commit()


def list_api_health(cabinet_id: str) -> list[dict[str, Any]]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM wb_api_health
            WHERE cabinet_id = ?
            ORDER BY section ASC
            """,
            (cabinet_id,),
        )
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "section": str(row["section"]),
                    "status": str(row["status"] or "unknown"),
                    "lastSuccessAt": row["last_success_at"],
                    "lastErrorAt": row["last_error_at"],
                    "lastErrorMessage": row["last_error_message"],
                    "rateLimitState": row["rate_limit_state"],
                    "message": row["message"],
                    "requiredAction": row["required_action"],
                }
            )
        return rows


def list_sync_jobs(cabinet_id: str) -> list[dict[str, Any]]:
    with _db_conn() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM wb_sync_jobs
            WHERE cabinet_id = ?
            ORDER BY started_at DESC, id DESC
            LIMIT 20
            """,
            (cabinet_id,),
        )
        rows = []
        for row in cur.fetchall():
            rows.append(
                {
                    "id": str(row["id"]),
                    "cabinetId": str(row["cabinet_id"]),
                    "type": str(row["type"]),
                    "status": str(row["status"]),
                    "startedAt": row["started_at"],
                    "finishedAt": row["finished_at"],
                    "durationMs": row["duration_ms"],
                    "recordsLoaded": int(row["records_loaded"] or 0),
                    "errorMessage": row["error_message"],
                    "runtimeSource": row["runtime_source"],
                    "meta": _parse_json(row["meta_json"], {}),
                }
            )
        return rows


def get_sync_status(cabinet_id: str) -> dict[str, Any]:
    jobs = list_sync_jobs(cabinet_id)
    latest = jobs[0] if jobs else None
    return {
        "cabinetId": cabinet_id,
        "latestJob": latest,
        "history": jobs,
    }


def get_connection_summary() -> dict[str, Any]:
    context = get_workspace_context(mode="live")
    cabinets = list_cabinets()
    connected = sum(1 for item in cabinets if item.get("connected"))
    return {
        "organization": context.get("organization"),
        "activeCabinet": context.get("cabinet"),
        "connectedCabinets": connected,
        "totalCabinets": len(cabinets),
        "hasActiveConnection": bool((context.get("cabinet") or {}).get("connected")),
        "lastChanged": context.get("lastChanged"),
    }


def set_active_cabinet_connection(connected: bool) -> dict[str, Any]:
    active = get_active_cabinet()
    if active["id"] == "wb_cabinet_unconfigured":
        virtual = dict(active)
        virtual["connected"] = connected
        virtual["status"] = "connected" if connected else "disconnected"
        virtual["lastSyncAt"] = _iso_now() if connected else None
        virtual["syncMessage"] = "Legacy compatibility mode without saved cabinet."
        return virtual
    now = _iso_now()
    with _db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE wb_cabinets
            SET connected = ?, status = ?, updated_at = ?, last_checked_at = ?
            WHERE id = ?
            """,
            (1 if connected else 0, "connected" if connected else "disconnected", now, now, active["id"]),
        )
        conn.commit()
    invalidate_workspace_caches()
    return get_cabinet(str(active["id"]))


def test_cabinet(cabinet_id: str) -> dict[str, Any]:
    cabinet = get_cabinet(cabinet_id)
    tokens = _load_cabinet_tokens(cabinet_id)
    today = date.today()
    yesterday = today - timedelta(days=1)
    checks: list[dict[str, Any]] = []

    def _record(section: str, status: str, message: str, details: dict[str, Any] | None = None) -> None:
        _set_health(cabinet_id, section, status, message=message, error=None if status in {"ok", "connected", "healthy", "partial"} else message)
        checks.append({"section": section, "status": status, "message": message, "details": details or {}})

    statistics_token = tokens.get("statistics") or tokens.get("seller")
    if statistics_token:
        sales_probe = inspect_sales_api(statistics_token, str(yesterday), str(today), telegram_id=int(cabinet["dataOwnerId"]))
        orders_probe = inspect_orders_api(statistics_token, str(yesterday), str(today), telegram_id=int(cabinet["dataOwnerId"]))
        sales_ok = str((sales_probe or {}).get("status") or "").upper() not in {"ERROR", "FAILED"}
        orders_ok = str((orders_probe or {}).get("status") or "").upper() not in {"ERROR", "FAILED"}
        if sales_ok or orders_ok:
            _record(
                "statistics",
                "ok" if sales_ok and orders_ok else "partial",
                "Statistics API отвечает.",
                {"sales": sales_probe, "orders": orders_probe},
            )
        else:
            _record("statistics", "error", "Statistics API не прошёл проверку.", {"sales": sales_probe, "orders": orders_probe})
    else:
        _record("statistics", "missing_token", "Не задан statistics token.")

    seller_token = tokens.get("seller") or tokens.get("statistics")
    if seller_token:
        _record("seller", "ok", "Seller token присутствует и будет использован для sync.")
    else:
        _record("seller", "missing_token", "Не задан seller token.")

    advertising_token = tokens.get("advertising")
    if advertising_token:
        advertising_probe = ads_probe(advertising_token, days=1, token_source="wb_cabinet")
        advertising_status = str((advertising_probe or {}).get("status") or "").upper()
        if advertising_status not in {"ERROR", "FAILED"}:
            _record("advertising", "ok", "Advertising API отвечает.", {"probe": advertising_probe})
        else:
            _record("advertising", "error", "Advertising API не прошёл проверку.", {"probe": advertising_probe})
    else:
        _record("advertising", "missing_token", "Не задан advertising token.")

    finance_token = tokens.get("finance")
    if finance_token:
        finance_probe = fetch_wb_finance_reports_list(str(yesterday), str(today), token=finance_token)
        finance_status = str((finance_probe or {}).get("status") or "")
        if finance_status not in {"ERROR", "FAILED"}:
            _record("finance", "ok", "Finance API отвечает.", {"probe": finance_probe})
        else:
            _record("finance", "error", "Finance API не прошёл проверку.", {"probe": finance_probe})
    else:
        _record("finance", "missing_token", "Не задан finance token.")

    passed = [item for item in checks if item["status"] in {"ok", "partial", "connected", "healthy"}]
    overall = "connected" if passed else "error"
    data_quality = "high" if len(passed) >= 3 else "medium" if len(passed) >= 1 else "pending"
    with _db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE wb_cabinets
            SET connected = ?, status = ?, data_quality = ?, last_checked_at = ?, updated_at = ?, sync_message = ?
            WHERE id = ?
            """,
            (
                1 if passed else 0,
                overall,
                data_quality,
                _iso_now(),
                _iso_now(),
                "Проверка токенов выполнена." if passed else "Часть токенов отсутствует или недействительна.",
                cabinet_id,
            ),
        )
        conn.commit()
    invalidate_workspace_caches()
    return {
        "cabinet": get_cabinet(cabinet_id),
        "checks": checks,
        "status": overall,
    }


def _insert_sync_job(cur: sqlite3.Cursor, cabinet_id: str, sync_type: str) -> str:
    job_id = f"sync_{uuid4().hex[:12]}"
    cur.execute(
        """
        INSERT INTO wb_sync_jobs(id, cabinet_id, type, status, started_at, runtime_source, meta_json)
        VALUES(?, ?, ?, 'running', ?, 'live', ?)
        """,
        (job_id, cabinet_id, sync_type, _iso_now(), _serialize_json({})),
    )
    return job_id


def _finish_sync_job(
    cur: sqlite3.Cursor,
    job_id: str,
    *,
    status: str,
    records_loaded: int,
    meta: dict[str, Any],
    error_message: str | None = None,
    started_at: datetime | None = None,
) -> None:
    finished_at = _utc_now()
    duration_ms = None
    if started_at is not None:
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    cur.execute(
        """
        UPDATE wb_sync_jobs
        SET status = ?, finished_at = ?, duration_ms = ?, records_loaded = ?, error_message = ?, meta_json = ?
        WHERE id = ?
        """,
        (status, finished_at.isoformat(), duration_ms, records_loaded, error_message, _serialize_json(meta), job_id),
    )


def _derive_records_loaded(result: Any) -> int:
    if isinstance(result, dict):
        for key in ("records_loaded", "rows_loaded", "inserted", "loaded", "rows_after_filter"):
            value = result.get(key)
            if isinstance(value, (int, float)):
                return int(value)
        summary = result.get("summary")
        if isinstance(summary, dict):
            return _derive_records_loaded(summary)
    return 0


def sync_cabinet(
    cabinet_id: str,
    *,
    sync_type: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    normalized_type = str(sync_type or "all").strip().lower()
    if normalized_type not in SYNC_TYPES:
        raise ValueError(f"Unsupported sync type: {sync_type}")
    cabinet = get_cabinet(cabinet_id)
    if cabinet["id"] == "wb_cabinet_unconfigured":
        raise ValueError("No WB cabinet configured.")
    tokens = _load_cabinet_tokens(cabinet_id)
    start = date.fromisoformat(date_from) if date_from else (date.today() - timedelta(days=30))
    end = date.fromisoformat(date_to) if date_to else date.today()
    if end < start:
        raise ValueError("date_to must be greater than or equal to date_from.")
    started_at = _utc_now()

    with _db_conn() as conn:
        cur = conn.cursor()
        job_id = _insert_sync_job(cur, cabinet_id, normalized_type)
        conn.commit()

    results: dict[str, Any] = {}
    records_loaded = 0
    failures: list[str] = []
    owner_id = int(cabinet["dataOwnerId"])

    def _run_block(section: str, runner) -> None:
        nonlocal records_loaded
        try:
            result = runner()
            results[section] = result
            records_loaded += _derive_records_loaded(result)
            _set_health(cabinet_id, section, "ok", message="Синхронизация выполнена.")
        except Exception as exc:
            failures.append(section)
            results[section] = {"status": "error", "message": str(exc)}
            _set_health(cabinet_id, section, "error", message="Синхронизация завершилась ошибкой.", error=str(exc))

    if normalized_type in {"sales", "orders", "all"}:
        statistics_token = tokens.get("statistics") or tokens.get("seller")
        if statistics_token:
            _run_block(
                "statistics",
                lambda: backfill_sales_orders_range(owner_id, statistics_token, str(start), str(end)),
            )
        else:
            failures.append("statistics")
            results["statistics"] = {"status": "missing_token"}
            _set_health(cabinet_id, "statistics", "missing_token", message="Не задан statistics token.")

    if normalized_type in {"stocks", "all"}:
        seller_token = tokens.get("seller") or tokens.get("statistics")
        if seller_token:
            _run_block("seller", lambda: load_stocks(owner_id, seller_token))
        else:
            failures.append("seller")
            results["seller"] = {"status": "missing_token"}
            _set_health(cabinet_id, "seller", "missing_token", message="Не задан seller token.")

    if normalized_type in {"advertising", "all"}:
        advertising_token = tokens.get("advertising")
        if advertising_token:
            _run_block(
                "advertising",
                lambda: backfill_advertising_period(owner_id, advertising_token, str(start), str(end), token_source="wb_cabinet"),
            )
        else:
            failures.append("advertising")
            results["advertising"] = {"status": "missing_token"}
            _set_health(cabinet_id, "advertising", "missing_token", message="Не задан advertising token.")

    if normalized_type in {"finance", "all"}:
        finance_token = tokens.get("finance")
        if finance_token:
            days = max((end - start).days + 1, 1)
            _run_block("finance", lambda: load_finance_expenses(owner_id, finance_token, days=days))
        else:
            failures.append("finance")
            results["finance"] = {"status": "missing_token"}
            _set_health(cabinet_id, "finance", "missing_token", message="Не задан finance token.")

    if normalized_type in {"products", "cards"}:
        results["products"] = {
            "status": "degraded",
            "message": "Отдельный live loader карточек не найден. Раздел Products использует синхронизированные продажи и остатки.",
        }

    status = "partial" if failures and len(failures) < len(results or {"sync": None}) else "success"
    if failures and len(failures) == len(results):
        status = "failed"
    if not failures:
        status = "success"

    with _db_conn() as conn:
        cur = conn.cursor()
        _finish_sync_job(
            cur,
            job_id,
            status=status,
            records_loaded=records_loaded,
            meta={
                "dateFrom": start.isoformat(),
                "dateTo": end.isoformat(),
                "results": results,
                "failedSections": failures,
            },
            error_message=", ".join(failures) if failures else None,
            started_at=started_at,
        )
        cur.execute(
            """
            UPDATE wb_cabinets
            SET connected = ?, status = ?, data_quality = ?, last_sync_status = ?, sync_message = ?,
                last_sync_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                1 if status in {"success", "partial"} else 0,
                "connected" if status in {"success", "partial"} else "error",
                "high" if status == "success" else "medium" if status == "partial" else "pending",
                status,
                "Синхронизация завершена." if status == "success" else "Синхронизация завершена частично." if status == "partial" else "Синхронизация не выполнена.",
                _iso_now() if status in {"success", "partial"} else None,
                _iso_now(),
                cabinet_id,
            ),
        )
        conn.commit()

    invalidate_workspace_caches()
    return {
        "job": get_sync_status(cabinet_id)["latestJob"],
        "cabinet": get_cabinet(cabinet_id),
        "results": results,
    }
