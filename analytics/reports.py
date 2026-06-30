from __future__ import annotations

from typing import Any

from analytics.cache import get_stale_cache_value
from analytics.common import DEFAULT_USER_ID, current_month_days
from analytics.executive import get_executive_payload
from analytics.business import get_business_payload
from analytics.finance import get_finance_payload
from analytics.advertising import get_advertising_payload
from analytics.products import get_products_payload
from analytics.inventory import get_inventory_payload
from analytics.advisor import get_advisor_payload


def get_reports_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    executive = get_executive_payload(user_id)
    business = get_business_payload(user_id)
    finance = get_finance_payload(user_id)
    advertising = get_advertising_payload(user_id)
    products = get_products_payload(user_id)
    inventory = get_inventory_payload(user_id)
    advisor = get_advisor_payload(user_id)

    catalog = [
        {"id": "report-ceo", "name": "CEO Report", "description": "Leadership-facing report from the analytics engine.", "category": "executive", "status": {"label": "Ready", "tone": "healthy"}, "updatedAt": end_date, "source": "Director", "href": "/executive"},
        {"id": "report-profit-audit", "name": "Profit Audit", "description": "Finance-safe profit audit and reconciliation report.", "category": "finance", "status": {"label": "Ready", "tone": "watch"}, "updatedAt": end_date, "source": "Financial Engine", "href": "/finance"},
        {"id": "report-ads", "name": "Advertising Analytics", "description": "Campaign efficiency, linkability, and ads health analytics.", "category": "advertising", "status": {"label": "Ready", "tone": "healthy"}, "updatedAt": end_date, "source": "Advertising Engine", "href": "/advertising"},
        {"id": "report-sku", "name": "SKU Analytics", "description": "Product and inventory-facing SKU analytics.", "category": "products", "status": {"label": "Ready", "tone": "healthy"}, "updatedAt": end_date, "source": "SKU Analytics", "href": "/products"},
    ]

    return {
        "summary": {
            "reportCount": len(catalog),
            "latestReport": "Advisor Snapshot",
            "latestSync": end_date,
            "latestCeoReport": "CEO Report",
            "latestProfitAudit": "Profit Audit",
            "systemStatus": executive.get("system", {}).get("status", "Operational"),
        },
        "catalog": catalog,
        "recent": [
            {"id": "recent-1", "date": end_date, "type": "Advisor Snapshot", "status": advisor.get("summary", {}).get("overallHealth", "Generated"), "source": "Advisor", "href": "/advisor"},
            {"id": "recent-2", "date": end_date, "type": "Profit Audit", "status": finance.get("summary", {}).get("status", "Generated"), "source": "Finance", "href": "/finance"},
        ],
        "templates": [
            {"id": "template-executive", "name": "Executive", "category": "executive", "status": "Ready"},
            {"id": "template-business", "name": "Business", "category": "business", "status": "Ready"},
            {"id": "template-finance", "name": "Finance", "category": "finance", "status": "Ready"},
            {"id": "template-advertising", "name": "Advertising", "category": "advertising", "status": "Ready"},
            {"id": "template-products", "name": "Products", "category": "products", "status": "Ready"},
            {"id": "template-inventory", "name": "Inventory", "category": "inventory", "status": "Ready"},
            {"id": "template-advisor", "name": "Advisor", "category": "advisor", "status": "Ready"},
        ],
        "exports": [
            {"format": "PDF", "status": "Planned", "description": "UI contract is ready for future PDF exports."},
            {"format": "Excel", "status": "Planned", "description": "UI contract is ready for future Excel exports."},
            {"format": "CSV", "status": "Planned", "description": "UI contract is ready for future CSV exports."},
            {"format": "JSON", "status": "Ready", "description": "Current API payloads are already JSON-native."},
        ],
        "timeline": [
            {"id": "reports-timeline-1", "title": "Reports registry refreshed", "description": "Reports center reuses current analytics engine services.", "severity": "low", "source": "Reports Engine"},
        ],
        "sources": [
            {"module": "executive", "health": executive.get("business_health", {}).get("status", "UNKNOWN"), "status": "Active", "lastUpdated": end_date},
            {"module": "business", "health": business.get("healthStatus", "UNKNOWN"), "status": "Active", "lastUpdated": end_date},
            {"module": "finance", "health": finance.get("summary", {}).get("health", "UNKNOWN"), "status": "Active", "lastUpdated": end_date},
            {"module": "advertising", "health": advertising.get("summary", {}).get("adsHealth", "UNKNOWN"), "status": "Active", "lastUpdated": end_date},
            {"module": "products", "health": "Healthy", "status": "Active", "lastUpdated": end_date},
            {"module": "inventory", "health": inventory.get("summary", {}).get("inventoryHealth", "UNKNOWN"), "status": "Active", "lastUpdated": end_date},
            {"module": "advisor", "health": advisor.get("summary", {}).get("overallHealth", "UNKNOWN"), "status": "Active", "lastUpdated": end_date},
            {"module": "system", "health": executive.get("system", {}).get("status", "UNKNOWN"), "status": "Operational", "lastUpdated": end_date},
        ],
        "lastUpdated": end_date,
    }


def _cached_snapshot(key: str) -> dict[str, Any]:
    return get_stale_cache_value(key) or {}


def get_reports_payload_fast(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    del user_id
    _, end_date = current_month_days()
    executive = _cached_snapshot("executive")
    business = _cached_snapshot("business")
    finance = _cached_snapshot("finance")
    advertising = _cached_snapshot("advertising")
    products = _cached_snapshot("products")
    inventory = _cached_snapshot("inventory")
    advisor = _cached_snapshot("advisor")
    system = _cached_snapshot("system")

    catalog = [
        {"id": "report-ceo", "name": "CEO Report", "description": "Leadership-facing report from cached executive metadata.", "category": "executive", "status": {"label": "Ready", "tone": "healthy"}, "updatedAt": end_date, "source": "Executive Cache", "href": "/executive"},
        {"id": "report-profit-audit", "name": "Profit Audit", "description": "Finance-safe profit audit entry from live finance cache.", "category": "finance", "status": {"label": "Ready", "tone": "watch"}, "updatedAt": end_date, "source": "Finance Cache", "href": "/finance"},
        {"id": "report-ads", "name": "Advertising Analytics", "description": "Advertising snapshot catalog entry.", "category": "advertising", "status": {"label": "Ready", "tone": "healthy"}, "updatedAt": end_date, "source": "Advertising Cache", "href": "/advertising"},
        {"id": "report-sku", "name": "SKU Analytics", "description": "Products and inventory report metadata.", "category": "products", "status": {"label": "Ready", "tone": "healthy"}, "updatedAt": end_date, "source": "Products Cache", "href": "/products"},
    ]

    return {
        "summary": {
            "reportCount": len(catalog),
            "latestReport": "Advisor Snapshot",
            "latestSync": end_date,
            "latestCeoReport": "CEO Report",
            "latestProfitAudit": "Profit Audit",
            "systemStatus": (system.get("status") or (executive.get("system") or {}).get("status") or "Operational"),
        },
        "catalog": catalog,
        "recent": [
            {"id": "recent-1", "date": end_date, "type": "Advisor Snapshot", "status": (advisor.get("summary") or {}).get("overallHealth", "Generated"), "source": "Advisor Cache", "href": "/advisor"},
            {"id": "recent-2", "date": end_date, "type": "Profit Audit", "status": (finance.get("summary") or {}).get("status", "Generated"), "source": "Finance Cache", "href": "/finance"},
        ],
        "templates": [
            {"id": "template-executive", "name": "Executive", "category": "executive", "status": "Ready"},
            {"id": "template-business", "name": "Business", "category": "business", "status": "Ready"},
            {"id": "template-finance", "name": "Finance", "category": "finance", "status": "Ready"},
            {"id": "template-advertising", "name": "Advertising", "category": "advertising", "status": "Ready"},
            {"id": "template-products", "name": "Products", "category": "products", "status": "Ready"},
            {"id": "template-inventory", "name": "Inventory", "category": "inventory", "status": "Ready"},
            {"id": "template-advisor", "name": "Advisor", "category": "advisor", "status": "Ready"},
        ],
        "exports": [
            {"format": "PDF", "status": "Planned", "description": "Fast mode returns export placeholders without generating files on demand."},
            {"format": "Excel", "status": "Planned", "description": "Fast mode avoids expensive export generation during runtime."},
            {"format": "CSV", "status": "Planned", "description": "CSV export remains a future runtime extension."},
            {"format": "JSON", "status": "Ready", "description": "Current API payloads are already JSON-native."},
        ],
        "timeline": [
            {"id": "reports-timeline-fast-1", "title": "Reports registry refreshed", "description": "Reports fast mode reused latest cached metadata and did not rebuild heavy reports.", "severity": "low", "source": "Reports Engine"},
        ],
        "sources": [
            {"module": "executive", "health": (executive.get("business_health") or {}).get("status", "UNKNOWN"), "status": "Cached", "lastUpdated": end_date},
            {"module": "business", "health": business.get("healthStatus", "UNKNOWN"), "status": "Live/Cache", "lastUpdated": end_date},
            {"module": "finance", "health": (finance.get("summary") or {}).get("health", "UNKNOWN"), "status": "Live/Cache", "lastUpdated": end_date},
            {"module": "advertising", "health": (advertising.get("summary") or {}).get("adsHealth", "UNKNOWN"), "status": "Live/Cache", "lastUpdated": end_date},
            {"module": "products", "health": "Healthy" if (products.get("summary") or {}).get("skuCount") else "UNKNOWN", "status": "Live/Cache", "lastUpdated": end_date},
            {"module": "inventory", "health": (inventory.get("summary") or {}).get("inventoryHealth", "UNKNOWN"), "status": "Live/Cache", "lastUpdated": end_date},
            {"module": "advisor", "health": (advisor.get("summary") or {}).get("overallHealth", "UNKNOWN"), "status": "Cached", "lastUpdated": end_date},
            {"module": "system", "health": system.get("status", "UNKNOWN"), "status": "Cached", "lastUpdated": end_date},
        ],
        "lastUpdated": end_date,
    }
