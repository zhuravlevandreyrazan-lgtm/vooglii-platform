from __future__ import annotations

from typing import Any

from analytics.common import BUILD_VERSION, PRODUCT_NAME, now_iso


def _message(reason: str) -> str:
    return reason or "Snapshot build timed out. Returning cached or degraded data."


def executive_degraded(reason: str) -> dict[str, Any]:
    return {
        "product": PRODUCT_NAME,
        "screen": "command_center",
        "period": {"label": "current_month", "date_from": None, "date_to": None},
        "business_health": {
            "score": 0,
            "status": "UNKNOWN",
            "summary": "Executive snapshot is temporarily degraded.",
            "confidence": 0,
            "data_mode": "degraded",
        },
        "executive_brief": {
            "title": "Degraded executive snapshot",
            "what_happened": [_message(reason)],
            "why": ["Heavy snapshot builder timed out or failed."],
            "actions": ["Retry request or use cached data on the next call."],
            "confidence": 0,
            "sources": ["degraded"],
        },
        "kpis": [],
        "workspaces": [],
        "today_actions": [],
        "critical_alerts": [{"id": "degraded-executive", "title": "Degraded mode", "detail": _message(reason), "status": "WARNING"}],
        "recent_events": [],
        "system": {
            "status": "DEGRADED",
            "finance_api": "UNKNOWN",
            "last_updated": now_iso(),
            "degraded": True,
            "degraded_notes": [_message(reason)],
        },
    }


def business_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
        "trends": {"revenue": 0, "profit": 0, "margin": 0, "returns": 0},
        "healthScore": 0,
        "healthStatus": "DEGRADED",
        "periods": {
            "today": {"key": "today", "label": "Today", "revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
            "yesterday": {"key": "yesterday", "label": "Yesterday", "revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
            "sevenDays": {"key": "sevenDays", "label": "7 Days", "revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
            "thirtyDays": {"key": "thirtyDays", "label": "30 Days", "revenue": 0, "profit": 0, "margin": 0, "orders": 0, "returns": 0, "averageOrderValue": 0, "unitsSold": 0},
        },
        "topProducts": [],
        "generatedAt": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def finance_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"operatingProfit": None, "officialProfit": None, "difference": None, "health": "DEGRADED", "trustScore": 0, "status": "degraded"},
        "quality": {"coverage": None, "residualUsage": "degraded", "trustScore": 0, "confidence": "Low", "health": "DEGRADED"},
        "difference": {"operatingProfit": None, "officialProfit": None, "difference": None, "differencePercent": None, "reason": _message(reason), "explanation": None},
        "metrics": [],
        "alerts": [{"id": "finance-degraded", "title": "Finance snapshot degraded", "description": _message(reason), "severity": "high", "source": "placeholder"}],
        "timeline": [],
        "lastUpdated": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def advertising_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"advertisingSpend": None, "linkedSpend": None, "unlinkedSpend": None, "roas": None, "acos": None, "adsHealth": "DEGRADED", "trust": "Low", "status": "degraded"},
        "health": {"adsHealth": "DEGRADED", "linkability": None, "duplicateSpend": None, "linkedPercent": None, "coverage": None, "status": "degraded"},
        "metrics": [],
        "recommendations": [],
        "alerts": [{"id": "ads-degraded", "title": "Advertising snapshot degraded", "description": _message(reason), "severity": "high", "source": "placeholder"}],
        "timeline": [],
        "campaigns": [],
        "lastUpdated": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def products_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"skuCount": 0, "activeSku": 0, "problemSku": 0, "riskSku": 0, "growthSku": 0, "lastUpdated": now_iso()},
        "products": [],
        "recommendations": [],
        "history": [],
        "inventoryPreview": [],
        "alerts": [{"id": "products-degraded", "title": "Products snapshot degraded", "description": _message(reason), "severity": "high", "source": "placeholder"}],
        "timeline": [],
        "actions": [],
        "lastUpdated": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def inventory_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"totalStock": None, "criticalSku": 0, "daysLeftAverage": None, "forecastCoverage": None, "inventoryHealth": "DEGRADED", "warehouseCount": None, "lastUpdated": now_iso()},
        "health": {"inventoryHealth": "DEGRADED", "coverage": None, "forecastConfidence": "Low", "criticalStock": 0, "lowStock": 0, "warehouseStatus": "degraded"},
        "items": [],
        "restockPlan": [],
        "supplyPriority": [],
        "warehouses": [],
        "history": [],
        "alerts": [{"id": "inventory-degraded", "title": "Inventory snapshot degraded", "description": _message(reason), "severity": "high", "source": "placeholder"}],
        "timeline": [],
        "metrics": [],
        "lastUpdated": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def advisor_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"businessStatus": "DEGRADED", "overallHealth": "DEGRADED", "criticalRisks": 0, "topOpportunities": 0, "recommendationCount": 0, "lastUpdated": now_iso()},
        "recommendations": [],
        "evidence": [],
        "risks": [],
        "opportunities": [],
        "priorities": [],
        "timeline": [],
        "actions": [],
        "sources": [],
        "conversation": {"placeholder": True, "prompt": _message(reason), "history": []},
        "insights": [],
        "lastUpdated": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def advisor_query_degraded(reason: str) -> dict[str, Any]:
    return {
        "status": "degraded",
        "answer": "Advisor query is temporarily running in safe degraded mode. Review the linked workspaces and retry after the backend recovers.",
        "summary": _message(reason),
        "recommendations": [
            {
                "id": "advisor-query-degraded-rec-1",
                "title": "Open Advisor workspace snapshot",
                "reason": "The conversational endpoint could not build a richer response.",
                "priority": "medium",
                "confidence": "Low",
                "href": "/advisor",
            }
        ],
        "evidence": [
            {
                "id": "advisor-query-degraded-evidence-1",
                "label": "Degraded mode",
                "detail": _message(reason),
                "metrics": ["source degraded", "confidence low"],
                "href": "/advisor",
            }
        ],
        "links": [
            {
                "id": "advisor-query-degraded-link-1",
                "label": "Advisor",
                "href": "/advisor",
                "description": "Open the advisor workspace snapshot while query mode is degraded.",
            }
        ],
        "related": [
            {
                "id": "advisor-query-degraded-related-1",
                "type": "workspace",
                "label": "Advisor workspace",
                "href": "/advisor",
                "note": "Fallback navigation target",
            }
        ],
        "confidence": 0.2,
    }


def reports_degraded(reason: str) -> dict[str, Any]:
    return {
        "summary": {"reportCount": 0, "latestReport": "Unavailable", "latestSync": now_iso(), "latestCeoReport": "Unavailable", "latestProfitAudit": "Unavailable", "systemStatus": "DEGRADED"},
        "catalog": [],
        "recent": [],
        "templates": [],
        "exports": [],
        "timeline": [],
        "sources": [],
        "lastUpdated": now_iso(),
        "status": "degraded",
        "data_quality": "low",
        "message": _message(reason),
    }


def system_degraded(reason: str) -> dict[str, Any]:
    return {
        "product": PRODUCT_NAME,
        "mode": "degraded",
        "status": "DEGRADED",
        "health": {},
        "quality": {},
        "adsHealth": {},
        "financeHealth": {},
        "cache": {},
        "writeSafety": {},
        "cooldowns": {},
        "lastUpdates": {},
        "coreV2Status": {},
        "controlCenter": {},
        "financeApi": {},
        "lastUpdated": now_iso(),
        "message": _message(reason),
    }
