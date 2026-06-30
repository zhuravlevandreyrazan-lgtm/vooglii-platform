from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_ORGANIZATIONS: list[dict[str, Any]] = [
    {
        "id": "org_vooglii_demo",
        "name": "VOOGLII Demo",
        "plan": "enterprise_demo",
        "status": "active",
        "createdAt": "2026-06-01T09:00:00Z",
        "health": "Healthy",
    },
    {
        "id": "org_test_seller",
        "name": "Test Seller",
        "plan": "growth",
        "status": "active",
        "createdAt": "2026-06-10T12:00:00Z",
        "health": "Watch",
    },
    {
        "id": "org_agency_demo",
        "name": "Agency Demo",
        "plan": "agency",
        "status": "active",
        "createdAt": "2026-06-15T15:00:00Z",
        "health": "Healthy",
    },
]

_CABINETS: list[dict[str, Any]] = [
    {
        "id": "cabinet_vooglii_main",
        "organizationId": "org_vooglii_demo",
        "name": "VOOGLII Main Cabinet",
        "sellerId": "WB-458210",
        "status": "connected",
        "connected": True,
        "lastSyncAt": "2026-06-30T09:45:00Z",
        "dataQuality": "high",
        "tokenStatus": "safe_placeholder",
        "health": "Healthy",
    },
    {
        "id": "cabinet_vooglii_home",
        "organizationId": "org_vooglii_demo",
        "name": "VOOGLII Home & Living",
        "sellerId": "WB-458211",
        "status": "connected",
        "connected": True,
        "lastSyncAt": "2026-06-30T09:42:00Z",
        "dataQuality": "high",
        "tokenStatus": "safe_placeholder",
        "health": "Healthy",
    },
    {
        "id": "cabinet_test_fashion",
        "organizationId": "org_test_seller",
        "name": "Test Seller Fashion",
        "sellerId": "WB-553901",
        "status": "connected",
        "connected": True,
        "lastSyncAt": "2026-06-30T08:55:00Z",
        "dataQuality": "medium",
        "tokenStatus": "safe_placeholder",
        "health": "Watch",
    },
    {
        "id": "cabinet_test_beauty",
        "organizationId": "org_test_seller",
        "name": "Test Seller Beauty",
        "sellerId": "WB-553902",
        "status": "disconnected",
        "connected": False,
        "lastSyncAt": None,
        "dataQuality": "pending",
        "tokenStatus": "safe_placeholder",
        "health": "Watch",
    },
    {
        "id": "cabinet_agency_brand_a",
        "organizationId": "org_agency_demo",
        "name": "Agency Brand A",
        "sellerId": "WB-771100",
        "status": "connected",
        "connected": True,
        "lastSyncAt": "2026-06-30T11:10:00Z",
        "dataQuality": "high",
        "tokenStatus": "safe_placeholder",
        "health": "Healthy",
    },
    {
        "id": "cabinet_agency_brand_b",
        "organizationId": "org_agency_demo",
        "name": "Agency Brand B",
        "sellerId": "WB-771101",
        "status": "connected",
        "connected": True,
        "lastSyncAt": "2026-06-30T10:58:00Z",
        "dataQuality": "medium",
        "tokenStatus": "safe_placeholder",
        "health": "Healthy",
    },
]

_STATE: dict[str, Any] = {
    "activeOrganizationId": _ORGANIZATIONS[0]["id"],
    "activeCabinetId": _CABINETS[0]["id"],
    "lastChanged": _now_iso(),
}


def _organization_cabinet_count(organization_id: str) -> int:
    return sum(1 for cabinet in _CABINETS if cabinet.get("organizationId") == organization_id)


def list_organizations() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _ORGANIZATIONS:
        row = deepcopy(item)
        row["cabinetCount"] = _organization_cabinet_count(str(item["id"]))
        rows.append(row)
    return rows


def get_organization(organization_id: str) -> dict[str, Any]:
    for item in list_organizations():
        if str(item.get("id")) == organization_id:
            return item
    raise KeyError(organization_id)


def list_cabinets(organization_id: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    org_map = {item["id"]: item["name"] for item in _ORGANIZATIONS}
    for item in _CABINETS:
        if organization_id and str(item.get("organizationId")) != organization_id:
            continue
        row = deepcopy(item)
        row["organizationName"] = org_map.get(str(item.get("organizationId")), "Unknown organization")
        rows.append(row)
    return rows


def get_cabinet(cabinet_id: str) -> dict[str, Any]:
    for item in list_cabinets():
        if str(item.get("id")) == cabinet_id:
            return item
    raise KeyError(cabinet_id)


def get_active_organization() -> dict[str, Any]:
    return get_organization(str(_STATE["activeOrganizationId"]))


def get_active_cabinet() -> dict[str, Any]:
    return get_cabinet(str(_STATE["activeCabinetId"]))


def _set_last_changed() -> None:
    _STATE["lastChanged"] = _now_iso()


def select_organization(organization_id: str) -> dict[str, Any]:
    organization = get_organization(organization_id)
    _STATE["activeOrganizationId"] = str(organization["id"])
    matching_cabinets = list_cabinets(str(organization["id"]))
    if matching_cabinets:
        _STATE["activeCabinetId"] = str(matching_cabinets[0]["id"])
    _set_last_changed()
    return get_workspace_context()


def select_cabinet(cabinet_id: str) -> dict[str, Any]:
    cabinet = get_cabinet(cabinet_id)
    _STATE["activeCabinetId"] = str(cabinet["id"])
    _STATE["activeOrganizationId"] = str(cabinet["organizationId"])
    _set_last_changed()
    return get_workspace_context()


def set_active_cabinet_connection(connected: bool) -> dict[str, Any]:
    active_cabinet_id = str(_STATE["activeCabinetId"])
    for item in _CABINETS:
        if str(item.get("id")) == active_cabinet_id:
            item["connected"] = connected
            item["status"] = "connected_dev" if connected else "disconnected_dev"
            item["lastSyncAt"] = _now_iso() if connected else None
            item["health"] = "Healthy" if connected else "Watch"
            if not connected and str(item.get("dataQuality")).lower() == "high":
                item["dataQuality"] = "pending"
            _set_last_changed()
            return get_cabinet(active_cabinet_id)
    raise KeyError(active_cabinet_id)


def get_workspace_context(mode: str = "dev") -> dict[str, Any]:
    organization = get_active_organization()
    cabinet = get_active_cabinet()
    return {
        "organizationId": organization["id"],
        "cabinetId": cabinet["id"],
        "mode": mode,
        "lastChanged": str(_STATE["lastChanged"]),
        "organizationCount": len(_ORGANIZATIONS),
        "cabinetCount": len(_CABINETS),
        "organization": organization,
        "cabinet": cabinet,
    }


def scoped_record(record: dict[str, Any], mode: str = "dev") -> dict[str, Any]:
    context = get_workspace_context(mode=mode)
    scoped = dict(record)
    scoped["organizationId"] = context["organizationId"]
    scoped["organizationName"] = context["organization"]["name"]
    scoped["cabinetId"] = context["cabinetId"]
    scoped["cabinetName"] = context["cabinet"]["name"]
    scoped["workspaceMode"] = context["mode"]
    return scoped


def scoped_records(records: list[dict[str, Any]], mode: str = "dev") -> list[dict[str, Any]]:
    return [scoped_record(record, mode=mode) for record in records]
