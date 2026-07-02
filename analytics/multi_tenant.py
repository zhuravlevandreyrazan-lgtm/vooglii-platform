from __future__ import annotations

from typing import Any

from analytics.wb_cabinet_manager import (
    get_active_cabinet,
    get_active_cabinet_user_id,
    get_active_organization,
    get_cabinet,
    get_organization,
    get_workspace_context,
    list_cabinets,
    list_organizations,
    scoped_record,
    scoped_records,
    select_cabinet,
    select_organization,
    set_active_cabinet_connection,
)

__all__ = [
    "get_active_cabinet",
    "get_active_cabinet_user_id",
    "get_active_organization",
    "get_cabinet",
    "get_organization",
    "get_workspace_context",
    "list_cabinets",
    "list_organizations",
    "scoped_record",
    "scoped_records",
    "select_cabinet",
    "select_organization",
    "set_active_cabinet_connection",
]


def scoped_record_passthrough(record: dict[str, Any], mode: str = "live") -> dict[str, Any]:
    return scoped_record(record, mode=mode)
