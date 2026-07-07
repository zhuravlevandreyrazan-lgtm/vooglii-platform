from __future__ import annotations

from typing import Any

import load_sales

from .advertising_loader import sync_advertising
from .finance_loader import sync_finance
from .orders_loader import sync_orders
from .products_loader import refresh_products_index
from .rate_limiter import (
    SYNC_API_LIMIT,
    SYNC_ERROR,
    SYNC_NO_TOKEN,
    SYNC_OK,
    SYNC_PARTIAL,
    SYNC_UNAVAILABLE,
    next_allowed_at,
    parse_status_kind,
)
from .sales_loader import sync_sales
from .stocks_loader import sync_stocks
from .sync_state import list_sync_state, save_sync_state
from .token_provider import resolve_sync_token


BLOCK_ORDER = ("sales", "orders", "finance", "advertising", "stocks", "products")


def _period_label(period: int | tuple[str, str]) -> str:
    if isinstance(period, tuple):
        return f"{period[0]}..{period[1]}"
    return f"last_{int(period)}_days"


def _run_block(user_id: int, block: str, raw_status: str, payload: dict[str, Any]) -> dict[str, Any]:
    sync_status = parse_status_kind(raw_status)
    status_reason = str(raw_status or "")
    last_success_at = load_sales._now_str() if sync_status == SYNC_OK else None
    block_next_allowed = next_allowed_at(user_id, block if block != "products" else "sales")
    save_sync_state(
        user_id,
        block,
        sync_status,
        status_reason=status_reason,
        last_success_at=last_success_at,
        next_allowed_at=block_next_allowed,
        rows_inserted=int(payload.get("inserted") or 0),
        rows_updated=int(payload.get("updated") or 0),
        rows_skipped=int(payload.get("skipped") or 0),
        rows_invalid=int(payload.get("invalid") or 0),
        source_rows=int(payload.get("source_rows") or 0),
        source_name=payload.get("source_name"),
        meta=payload.get("meta") or {},
    )
    return {
        "status": sync_status,
        "raw_status": status_reason,
        "next_allowed_at": block_next_allowed,
        "rows_inserted": int(payload.get("inserted") or 0),
        "rows_updated": int(payload.get("updated") or 0),
        "rows_skipped": int(payload.get("skipped") or 0),
        "rows_invalid": int(payload.get("invalid") or 0),
        "source_rows": int(payload.get("source_rows") or 0),
        "source_name": payload.get("source_name"),
        "meta": payload.get("meta") or {},
    }


def _overall_status(blocks: dict[str, dict[str, Any]]) -> str:
    statuses = [str((blocks.get(name) or {}).get("status") or SYNC_ERROR) for name in BLOCK_ORDER if name in blocks]
    if statuses and all(item == SYNC_OK for item in statuses):
        return SYNC_OK
    if any(item == SYNC_OK for item in statuses):
        return SYNC_PARTIAL
    if statuses and all(item in (SYNC_API_LIMIT, SYNC_UNAVAILABLE, SYNC_NO_TOKEN) for item in statuses):
        return statuses[0] if len(set(statuses)) == 1 else SYNC_PARTIAL
    return SYNC_ERROR


def run_sync(user_id: int, token: str | None = None, days: int = 30) -> dict[str, Any]:
    resolved = resolve_sync_token(user_id, token)
    period: int | tuple[str, str] = int(days)
    result: dict[str, Any] = {
        "user_id": int(user_id),
        "period": _period_label(period),
        "token_source": resolved.source,
        "blocks": {},
    }
    if not resolved.token:
        for block in BLOCK_ORDER:
            result["blocks"][block] = _run_block(
                user_id,
                block,
                "NO_TOKEN",
                {"source_name": None, "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {"reason": resolved.reason}},
            )
        result["overall_status"] = SYNC_NO_TOKEN
        result["sync_state"] = list_sync_state(user_id)
        return result

    sales_payload = sync_sales(user_id, resolved.token, period)
    result["blocks"]["sales"] = _run_block(user_id, "sales", sales_payload.get("raw_status"), sales_payload)
    orders_payload = sync_orders(user_id, resolved.token, period)
    result["blocks"]["orders"] = _run_block(user_id, "orders", orders_payload.get("raw_status"), orders_payload)
    finance_payload = sync_finance(user_id, resolved.token, period)
    result["blocks"]["finance"] = _run_block(user_id, "finance", finance_payload.get("raw_status"), finance_payload)
    ads_payload = sync_advertising(user_id, resolved.token, period)
    result["blocks"]["advertising"] = _run_block(user_id, "advertising", ads_payload.get("raw_status"), ads_payload)
    stocks_payload = sync_stocks(user_id, resolved.token, period)
    result["blocks"]["stocks"] = _run_block(user_id, "stocks", stocks_payload.get("raw_status"), stocks_payload)
    products_payload = refresh_products_index(user_id)
    products_payload["source_name"] = "local.sales_to_products"
    products_payload["meta"] = {"preserve_cost_dictionary": True}
    result["blocks"]["products"] = _run_block(user_id, "products", "SUCCESS", products_payload)
    result["overall_status"] = _overall_status(result["blocks"])
    result["sync_state"] = list_sync_state(user_id)
    return result


def run_backfill_sync(user_id: int, date_from: str, date_to: str, token: str | None = None) -> dict[str, Any]:
    resolved = resolve_sync_token(user_id, token)
    period: int | tuple[str, str] = (str(date_from), str(date_to))
    result: dict[str, Any] = {
        "user_id": int(user_id),
        "period": _period_label(period),
        "token_source": resolved.source,
        "blocks": {},
    }
    if not resolved.token:
        for block in BLOCK_ORDER:
            result["blocks"][block] = _run_block(
                user_id,
                block,
                "NO_TOKEN",
                {"source_name": None, "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {"reason": resolved.reason}},
            )
        result["overall_status"] = SYNC_NO_TOKEN
        result["sync_state"] = list_sync_state(user_id)
        return result
    result["blocks"]["sales"] = _run_block(user_id, "sales", (payload := sync_sales(user_id, resolved.token, period)).get("raw_status"), payload)
    result["blocks"]["orders"] = _run_block(user_id, "orders", (payload := sync_orders(user_id, resolved.token, period)).get("raw_status"), payload)
    result["blocks"]["finance"] = _run_block(user_id, "finance", (payload := sync_finance(user_id, resolved.token, period)).get("raw_status"), payload)
    result["blocks"]["advertising"] = _run_block(user_id, "advertising", (payload := sync_advertising(user_id, resolved.token, period)).get("raw_status"), payload)
    result["blocks"]["stocks"] = _run_block(user_id, "stocks", (payload := sync_stocks(user_id, resolved.token, period)).get("raw_status"), payload)
    products_payload = refresh_products_index(user_id)
    products_payload["source_name"] = "local.sales_to_products"
    products_payload["meta"] = {"preserve_cost_dictionary": True}
    result["blocks"]["products"] = _run_block(user_id, "products", "SUCCESS", products_payload)
    result["overall_status"] = _overall_status(result["blocks"])
    result["sync_state"] = list_sync_state(user_id)
    return result
