from __future__ import annotations

from typing import Any

import load_sales
from product_catalog import sync_product_catalog
from vooglii_finance.bridges import normalize_finance_expense_events
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict

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
from .sync_queue import (
    QUEUE_WAIT_LIMIT,
    enqueue_sync_task,
    record_sync_history,
)
from .sync_state import list_sync_state, save_sync_state
from .token_provider import resolve_sync_token


BLOCK_ORDER = ("sales", "orders", "finance", "advertising", "stocks", "products", "cost")


def _period_label(period: int | tuple[str, str]) -> str:
    if isinstance(period, tuple):
        return f"{period[0]}..{period[1]}"
    return f"last_{int(period)}_days"


def _period_dates(period: int | tuple[str, str]) -> tuple[str, str]:
    if isinstance(period, tuple):
        return str(period[0]), str(period[1])
    date_from, date_to = load_sales._normalize_period_dates(int(period))
    return str(date_from), str(date_to)


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


def _register_queue_and_history(user_id: int, block: str, period: int | tuple[str, str], result: dict[str, Any]) -> None:
    period_from, period_to = _period_dates(period)
    status = str(result.get("status") or "")
    raw_status = str(result.get("raw_status") or "")
    retry_at = result.get("next_allowed_at")
    if status == SYNC_API_LIMIT:
        enqueue_sync_task(
            user_id,
            block,
            period_from,
            period_to,
            status=QUEUE_WAIT_LIMIT,
            run_after=retry_at,
            last_error=raw_status,
        )
    record_sync_history(
        user_id,
        block,
        status or SYNC_ERROR,
        source_rows=int(result.get("source_rows") or 0),
        retry_at=retry_at,
        message=raw_status,
    )


def _loader_for_block(block: str):
    return {
        "sales": sync_sales,
        "orders": sync_orders,
        "finance": sync_finance,
        "advertising": sync_advertising,
        "stocks": sync_stocks,
        "products": refresh_products_index,
    }.get(str(block))


def _run_products_block(user_id: int, period: int | tuple[str, str]) -> dict[str, Any]:
    payload = refresh_products_index(user_id, period)
    payload["source_name"] = "product_catalog_v2"
    payload["meta"] = {**dict(payload.get("meta") or {}), "preserve_cost_dictionary": True}
    return _run_block(user_id, "products", "SUCCESS", payload)


def _run_cost_block(user_id: int, period: int | tuple[str, str]) -> dict[str, Any]:
    payload = refresh_products_index(user_id, period)
    payload["source_name"] = "product_catalog_v2.cost_coverage"
    return _run_block(user_id, "cost", str(payload.get("raw_status") or "SUCCESS"), payload)


def run_post_sync_rebuild(user_id: int, period: int | tuple[str, str]) -> dict[str, Any]:
    period_from, period_to = _period_dates(period)
    finance_bridge = normalize_finance_expense_events(int(user_id), period_from, period_to)
    catalog_sync = sync_product_catalog(int(user_id), period=(period_from, period_to))
    snapshot = build_unified_financial_snapshot_dict(int(user_id), (period_from, period_to))
    return {
        "status": "OK",
        "period_from": period_from,
        "period_to": period_to,
        "finance_bridge": finance_bridge,
        "catalog_sync": catalog_sync,
        "snapshot_audit": snapshot.get("snapshot_audit") or {},
    }


def run_single_block_sync(user_id: int, block: str, period: int | tuple[str, str], token: str | None = None) -> dict[str, Any]:
    if str(block) == "products":
        result = _run_products_block(user_id, period)
        _register_queue_and_history(user_id, "products", period, result)
        return result
    if str(block) == "cost":
        result = _run_cost_block(user_id, period)
        _register_queue_and_history(user_id, "cost", period, result)
        return result
    resolved = resolve_sync_token(user_id, token)
    if not resolved.token:
        result = _run_block(
            user_id,
            block,
            "NO_TOKEN",
            {"source_name": None, "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {"reason": resolved.reason}},
        )
        _register_queue_and_history(user_id, block, period, result)
        return result
    loader = _loader_for_block(block)
    if loader is None:
        result = _run_block(
            user_id,
            block,
            "EXCEPTION:UNKNOWN_BLOCK",
            {"source_name": None, "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {"block": block}},
        )
        _register_queue_and_history(user_id, block, period, result)
        return result
    payload = loader(user_id, resolved.token, period)
    result = _run_block(user_id, block, str(payload.get("raw_status") or "ERROR"), payload)
    _register_queue_and_history(user_id, block, period, result)
    return result


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
    period_from, period_to = _period_dates(period)
    result: dict[str, Any] = {
        "user_id": int(user_id),
        "period": _period_label(period),
        "period_from": period_from,
        "period_to": period_to,
        "token_source": resolved.source,
        "blocks": {},
    }
    if not resolved.token:
        for block in BLOCK_ORDER:
            block_result = _run_block(
                user_id,
                block,
                "NO_TOKEN",
                {"source_name": None, "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {"reason": resolved.reason}},
            )
            result["blocks"][block] = block_result
            _register_queue_and_history(user_id, block, period, block_result)
        result["overall_status"] = SYNC_NO_TOKEN
        result["sync_state"] = list_sync_state(user_id)
        return result

    for block in ("sales", "orders", "finance", "advertising", "stocks"):
        block_result = run_single_block_sync(user_id, block, period, token=resolved.token)
        result["blocks"][block] = block_result
    result["blocks"]["products"] = run_single_block_sync(user_id, "products", period, token=resolved.token)
    result["blocks"]["cost"] = run_single_block_sync(user_id, "cost", period, token=resolved.token)
    result["overall_status"] = _overall_status(result["blocks"])
    result["sync_state"] = list_sync_state(user_id)
    return result


def run_backfill_sync(user_id: int, date_from: str, date_to: str, token: str | None = None) -> dict[str, Any]:
    resolved = resolve_sync_token(user_id, token)
    period: int | tuple[str, str] = (str(date_from), str(date_to))
    result: dict[str, Any] = {
        "user_id": int(user_id),
        "period": _period_label(period),
        "period_from": str(date_from),
        "period_to": str(date_to),
        "token_source": resolved.source,
        "blocks": {},
    }
    if not resolved.token:
        for block in BLOCK_ORDER:
            block_result = _run_block(
                user_id,
                block,
                "NO_TOKEN",
                {"source_name": None, "source_rows": 0, "inserted": 0, "updated": 0, "skipped": 0, "invalid": 0, "meta": {"reason": resolved.reason}},
            )
            result["blocks"][block] = block_result
            _register_queue_and_history(user_id, block, period, block_result)
        result["overall_status"] = SYNC_NO_TOKEN
        result["sync_state"] = list_sync_state(user_id)
        return result
    for block in ("sales", "orders", "finance", "advertising", "stocks"):
        result["blocks"][block] = run_single_block_sync(user_id, block, period, token=resolved.token)
    result["blocks"]["products"] = run_single_block_sync(user_id, "products", period, token=resolved.token)
    result["blocks"]["cost"] = run_single_block_sync(user_id, "cost", period, token=resolved.token)
    result["overall_status"] = _overall_status(result["blocks"])
    result["sync_state"] = list_sync_state(user_id)
    return result
