from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.cache import get_stale_cache_value
from analytics.common import DEFAULT_USER_ID, current_month_days, route_for_workspace, safe_list, safe_text, snapshot_context, status_to_severity
from analytics.degraded import advisor_query_degraded


def _normalize_workspace_name(value: str | None) -> str:
    normalized = safe_text(value, "advisor").strip().lower()
    mapping = {
        "ads": "advertising",
        "product": "products",
        "inventory": "inventory",
        "report": "reports",
        "command-center": "executive",
        "ai": "advisor",
    }
    return mapping.get(normalized, normalized)


def _query_profile(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    text = safe_text(message, "").lower()
    workspace = _normalize_workspace_name((context or {}).get("workspace"))
    if any(token in text for token in ("прибыл", "profit", "margin", "финанс")):
        workspace = "finance"
    elif any(token in text for token in ("реклам", "ads", "roas", "acos", "campaign")):
        workspace = "advertising"
    elif any(token in text for token in ("sku", "товар", "product", "scale")):
        workspace = "products"
    elif any(token in text for token in ("stock", "inventory", "остат", "попол")):
        workspace = "inventory"
    elif any(token in text for token in ("business", "бизнес")):
        workspace = "business"
    elif any(token in text for token in ("executive", "директор", "ceo")):
        workspace = "executive"
    return {
        "workspace": workspace if workspace in {"advisor", "executive", "business", "finance", "advertising", "products", "inventory", "reports"} else "advisor",
        "text": text,
    }


def _query_links(profile_workspace: str, sku: str | None = None) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = [
        {
            "id": "advisor-link-advisor",
            "label": "Advisor",
            "href": "/advisor",
            "description": "Advisor workspace snapshot and conversation history.",
        }
    ]
    workspace_targets = [
        ("finance", "Finance", "Finance workspace and profitability review."),
        ("advertising", "Advertising", "Advertising health and campaign analysis."),
        ("products", "Products", "Products workspace with SKU-level overview."),
        ("inventory", "Inventory", "Inventory planning and stock coverage."),
        ("business", "Business", "Business KPI and trend workspace."),
        ("executive", "Executive", "Executive summary workspace."),
        ("reports", "Reports", "Reports center and exports."),
    ]
    for workspace, label, description in workspace_targets:
        if workspace == profile_workspace or profile_workspace == "advisor":
            links.insert(
                0,
                {
                    "id": f"advisor-link-{workspace}",
                    "label": label,
                    "href": route_for_workspace(workspace),
                    "description": description,
                },
            )
            break
    if sku:
        links.append(
            {
                "id": "advisor-link-product-sku",
                "label": f"Product {sku}",
                "href": f"/products/{sku}",
                "description": "Open product drilldown for the related SKU.",
            }
        )
        links.append(
            {
                "id": "advisor-link-inventory-sku",
                "label": f"Inventory {sku}",
                "href": f"/inventory/{sku}",
                "description": "Open inventory drilldown for the related SKU.",
            }
        )
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in links:
        href = str(item.get("href") or "")
        if href in seen:
            continue
        seen.add(href)
        unique.append(item)
    return unique[:6]


def get_advisor_query_payload(
    message: str,
    context: dict[str, Any] | None = None,
    user_id: int = DEFAULT_USER_ID,
) -> dict[str, Any]:
    profile = _query_profile(message, context)
    workspace = str(profile["workspace"])
    sku = safe_text((context or {}).get("sku"), "") or None
    advisor_snapshot = get_advisor_payload_fast(user_id)
    recommendations = list(advisor_snapshot.get("recommendations") or [])
    evidence = list(advisor_snapshot.get("evidence") or [])
    insights = list(advisor_snapshot.get("insights") or [])
    summary_snapshot = advisor_snapshot.get("summary") or {}

    filtered_recommendations = [
        item for item in recommendations if safe_text(item.get("source"), "executive") == workspace
    ] or recommendations[:3]
    filtered_evidence = [
        item for item in evidence if safe_text(item.get("workspace"), "executive") == workspace
    ] or evidence[:3]

    answer_lines = []
    if workspace == "finance":
        answer_lines.append("Start with finance confidence before using official profit to make management decisions.")
    elif workspace == "advertising":
        answer_lines.append("Start with advertising efficiency and isolate the campaigns where spend quality is drifting.")
    elif workspace == "products":
        answer_lines.append("Focus on the SKU set where growth potential is still healthy but operating risk is rising.")
    elif workspace == "inventory":
        answer_lines.append("Prioritize stock continuity first, especially where coverage is tightening on active SKUs.")
    elif workspace == "business":
        answer_lines.append("Use the business workspace to verify whether the current trend supports selective scaling.")
    elif workspace == "executive":
        answer_lines.append("Use the executive workspace to confirm the highest-priority cross-workspace decisions for today.")
    else:
        answer_lines.append("Use the advisor snapshot as a routing layer across finance, advertising, products, inventory, and executive views.")

    if filtered_recommendations:
        top_rec = filtered_recommendations[0]
        answer_lines.append(safe_text(top_rec.get("reason"), "A top recommendation is available for review."))
        answer_lines.append(safe_text(top_rec.get("expectedEffect"), "Open the linked workspace for the next step."))

    summary_text = safe_text(
        (insights[0] or {}).get("summary") if insights else summary_snapshot.get("businessStatus"),
        "Advisor summary is available from the current snapshot.",
    )

    response = {
        "status": "ok",
        "answer": " ".join(answer_lines).strip(),
        "summary": summary_text,
        "recommendations": [
            {
                "id": safe_text(item.get("id"), f"advisor-query-rec-{index}"),
                "title": safe_text(item.get("title"), "Recommendation"),
                "reason": safe_text(item.get("reason"), "No reason provided."),
                "priority": safe_text(item.get("priority"), "info").lower(),
                "confidence": safe_text(item.get("confidence"), "Unknown"),
                "href": safe_text(item.get("href"), "/advisor"),
            }
            for index, item in enumerate(filtered_recommendations[:3], 1)
        ],
        "evidence": [
            {
                "id": safe_text(item.get("id"), f"advisor-query-evidence-{index}"),
                "label": safe_text(item.get("source"), "Evidence"),
                "detail": safe_text(item.get("reason"), "No evidence detail provided."),
                "metrics": safe_list(item.get("metrics"))[:3],
                "href": safe_text(item.get("href"), "/advisor"),
            }
            for index, item in enumerate(filtered_evidence[:3], 1)
        ],
        "links": _query_links(workspace, sku),
        "related": [
            {
                "id": f"advisor-related-workspace-{workspace}",
                "type": "workspace",
                "label": workspace.title(),
                "href": route_for_workspace(workspace),
                "note": "Primary workspace linked to this advisor response.",
            }
        ],
        "confidence": 0.72 if filtered_recommendations else 0.45,
    }
    if sku:
        response["related"].append(
            {
                "id": f"advisor-related-sku-{sku}",
                "type": "sku",
                "label": sku,
                "href": f"/products/{sku}",
                "note": "Related SKU from advisor query context.",
            }
        )
    if workspace == "advertising":
        response["related"].append(
            {
                "id": "advisor-related-campaign-cluster",
                "type": "campaign",
                "label": "Advertising efficiency cluster",
                "href": "/advertising",
                "note": "Campaign-level review remains linked through the advertising workspace.",
            }
        )
    if workspace in {"finance", "business", "executive"}:
        response["related"].append(
            {
                "id": "advisor-related-report",
                "type": "report",
                "label": "Management report center",
                "href": "/reports",
                "note": "Use reports for exportable follow-up material.",
            }
        )
    return response


def get_advisor_query_degraded_payload(reason: str) -> dict[str, Any]:
    return advisor_query_degraded(reason)


def get_advisor_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    advisor = telegram_bot._advisor_v2_snapshot(user_id, (start_date, end_date), context=context)
    director = telegram_bot._director_snapshot(user_id, (start_date, end_date), context=context)

    recommendations = []
    for index, item in enumerate(list(advisor.get("recommendations") or []), 1):
        recommendations.append(
            {
                "id": f"advisor-rec-{index}",
                "title": safe_text(item.get("title"), "Recommendation"),
                "reason": safe_text(item.get("message") or item.get("basis"), "No reason provided."),
                "priority": str(item.get("priority") or "medium").lower(),
                "confidence": safe_text(item.get("confidence"), "Unknown").title(),
                "source": {
                    "FINANCE": "finance",
                    "ADS": "advertising",
                    "SKU": "products",
                    "DATA": "business",
                    "CASHFLOW": "business",
                    "STRATEGY": "executive",
                }.get(str(item.get("category") or "").upper(), "executive"),
                "expectedEffect": safe_text(item.get("action"), "Review manually."),
                "status": safe_text(item.get("category"), "Pending"),
                "href": route_for_workspace({
                    "FINANCE": "finance",
                    "ADS": "advertising",
                    "SKU": "products",
                    "DATA": "business",
                    "CASHFLOW": "business",
                    "STRATEGY": "executive",
                }.get(str(item.get("category") or "").upper(), "executive")),
            }
        )

    return {
        "summary": {
            "businessStatus": safe_text(director.get("business_health"), "Unknown"),
            "overallHealth": safe_text(advisor.get("status"), "Unknown"),
            "criticalRisks": len(list(advisor.get("risks") or [])),
            "topOpportunities": len(list(advisor.get("do_later") or [])),
            "recommendationCount": len(recommendations),
            "lastUpdated": end_date,
        },
        "recommendations": recommendations,
        "evidence": [
            {
                "id": f"advisor-evidence-{index}",
                "workspace": recommendation["source"],
                "source": recommendation["title"],
                "reason": recommendation["reason"],
                "metrics": [recommendation["expectedEffect"]],
                "href": recommendation["href"],
            }
            for index, recommendation in enumerate(recommendations[:5], 1)
        ],
        "risks": [
            {
                "title": item,
                "severity": status_to_severity("CRITICAL" if index == 0 else "WARNING"),
                "source": "finance" if "finance" in item.lower() else "executive",
            }
            for index, item in enumerate(list(advisor.get("risks") or []))
        ],
        "opportunities": [
            {
                "title": item,
                "impact": item,
                "source": "business",
            }
            for item in list(advisor.get("do_later") or [])[:4]
        ],
        "priorities": [
            {"label": "Critical", "value": len(list(advisor.get("action_groups", {}).get("critical") or []))},
            {"label": "Recommended", "value": len(list(advisor.get("action_groups", {}).get("recommended") or []))},
            {"label": "Optional", "value": len(list(advisor.get("action_groups", {}).get("optional") or []))},
        ],
        "timeline": [
            {
                "id": "advisor-timeline-1",
                "title": "Advisor snapshot refreshed",
                "description": safe_text((advisor.get("business_state") or {}).get("summary"), "Advisor snapshot updated."),
                "severity": status_to_severity(advisor.get("status")),
                "source": "advisor",
            }
        ],
        "actions": [
            {"id": f"advisor-action-{index}", "label": item, "href": "/executive"}
            for index, item in enumerate(list(advisor.get("do_now") or [])[:5], 1)
        ],
        "sources": [
            {"module": "executive", "status": safe_text(director.get("status"), "Unknown"), "health": safe_text(director.get("business_health"), "Unknown"), "lastUpdated": end_date, "source": "Director"},
            {"module": "finance", "status": safe_text(advisor.get("status"), "Unknown"), "health": safe_text((advisor.get("business_state") or {}).get("finance"), "Unknown"), "lastUpdated": end_date, "source": "Advisor v2"},
        ],
        "conversation": {
            "placeholder": True,
            "prompt": "Conversation endpoint can connect later without changing the current advisor workspace contract.",
            "history": [],
        },
        "insights": [
            {
                "id": "advisor-insight-1",
                "title": safe_text((advisor.get("main_recommendation") or {}).get("title"), "Advisor insight"),
                "summary": safe_text((advisor.get("business_state") or {}).get("summary"), "Advisor summary unavailable."),
                "tone": "watch",
            }
        ],
        "lastUpdated": end_date,
    }


def _cached_snapshot(key: str) -> dict[str, Any]:
    return get_stale_cache_value(key) or {}


def get_advisor_payload_fast(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    del user_id
    _, end_date = current_month_days()
    business = _cached_snapshot("business")
    finance = _cached_snapshot("finance")
    advertising = _cached_snapshot("advertising")
    products = _cached_snapshot("products")
    inventory = _cached_snapshot("inventory")
    executive = _cached_snapshot("executive")

    recommendations: list[dict[str, Any]] = []
    finance_health = safe_text((finance.get("summary") or {}).get("health"), "UNKNOWN")
    if finance_health not in ("GOOD", "UNKNOWN"):
        recommendations.append(
            {
                "id": "advisor-rec-finance",
                "title": "Review finance explainability before using official profit",
                "reason": safe_text((finance.get("difference") or {}).get("reason"), "Finance confidence remains limited."),
                "priority": "high",
                "confidence": safe_text((finance.get("quality") or {}).get("confidence"), "Medium").title(),
                "source": "finance",
                "expectedEffect": "Protect management decisions from overexplained finance data.",
                "status": finance_health,
                "href": route_for_workspace("finance"),
            }
        )
    if safe_text((advertising.get("summary") or {}).get("status"), "UNKNOWN") not in ("GOOD", "UNKNOWN"):
        recommendations.append(
            {
                "id": "advisor-rec-ads",
                "title": "Audit advertising efficiency",
                "reason": safe_text((advertising.get("summary") or {}).get("status"), "Advertising status requires review."),
                "priority": "medium",
                "confidence": safe_text((advertising.get("summary") or {}).get("trust"), "Medium").title(),
                "source": "advertising",
                "expectedEffect": "Reduce wasted spend and recover contribution margin.",
                "status": safe_text((advertising.get("summary") or {}).get("adsHealth"), "WATCH"),
                "href": route_for_workspace("advertising"),
            }
        )
    if safe_text((inventory.get("summary") or {}).get("inventoryHealth"), "UNKNOWN") not in ("GOOD", "UNKNOWN"):
        recommendations.append(
            {
                "id": "advisor-rec-inventory",
                "title": "Protect stock coverage on pressured SKUs",
                "reason": safe_text((inventory.get("health") or {}).get("warehouseStatus"), "Inventory coverage is under pressure."),
                "priority": "high",
                "confidence": safe_text((inventory.get("health") or {}).get("forecastConfidence"), "Medium").title(),
                "source": "inventory",
                "expectedEffect": "Avoid stockouts on active products.",
                "status": safe_text((inventory.get("summary") or {}).get("inventoryHealth"), "WATCH"),
                "href": route_for_workspace("inventory"),
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "id": "advisor-rec-fallback",
                "title": "Refresh stable workspaces to warm advisor cache",
                "reason": "Advisor fast mode builds from the latest cached workspace analytics.",
                "priority": "low",
                "confidence": "Low",
                "source": "executive",
                "expectedEffect": "Improves the quality of the next advisor response without changing backend logic.",
                "status": "Pending",
                "href": route_for_workspace("executive"),
            }
        )

    return {
        "summary": {
            "businessStatus": safe_text(business.get("healthStatus"), "Unknown"),
            "overallHealth": safe_text((executive.get("business_health") or {}).get("status"), "Unknown"),
            "criticalRisks": len([item for item in recommendations if item["priority"] == "high"]),
            "topOpportunities": len([item for item in recommendations if item["priority"] in ("low", "medium")]),
            "recommendationCount": len(recommendations),
            "lastUpdated": end_date,
        },
        "recommendations": recommendations,
        "evidence": [
            {
                "id": f"advisor-evidence-{index}",
                "workspace": recommendation["source"],
                "source": recommendation["title"],
                "reason": recommendation["reason"],
                "metrics": [recommendation["expectedEffect"]],
                "href": recommendation["href"],
            }
            for index, recommendation in enumerate(recommendations[:5], 1)
        ],
        "risks": [
            {
                "title": recommendation["reason"],
                "severity": status_to_severity("CRITICAL" if recommendation["priority"] == "high" else "WARNING"),
                "source": recommendation["source"],
            }
            for recommendation in recommendations[:4]
        ],
        "opportunities": [
            {
                "title": safe_text((products.get("recommendations") or [{}])[0].get("recommendation"), "Review product opportunities"),
                "impact": safe_text((products.get("recommendations") or [{}])[0].get("expectedEffect"), "Opportunity detail is not available."),
                "source": "products",
            }
        ],
        "priorities": [
            {"label": "Critical", "value": len([item for item in recommendations if item["priority"] == "high"])},
            {"label": "Recommended", "value": len([item for item in recommendations if item["priority"] == "medium"])},
            {"label": "Optional", "value": len([item for item in recommendations if item["priority"] == "low"])},
        ],
        "timeline": [
            {
                "id": "advisor-fast-timeline-1",
                "title": "Advisor fast snapshot refreshed",
                "description": "Advisor fast mode used the latest workspace caches and runtime diagnostics.",
                "severity": "low",
                "source": "advisor",
            }
        ],
        "actions": [
            {"id": f"advisor-action-{index}", "label": recommendation["title"], "href": recommendation["href"]}
            for index, recommendation in enumerate(recommendations[:5], 1)
        ],
        "sources": [
            {"module": "business", "status": safe_text(business.get("healthStatus"), "Unknown"), "health": safe_text(business.get("healthStatus"), "Unknown"), "lastUpdated": end_date, "source": "Business Cache"},
            {"module": "finance", "status": finance_health, "health": safe_text((finance.get("quality") or {}).get("confidence"), "Unknown"), "lastUpdated": end_date, "source": "Finance Cache"},
            {"module": "advertising", "status": safe_text((advertising.get("summary") or {}).get("adsHealth"), "Unknown"), "health": safe_text((advertising.get("summary") or {}).get("status"), "Unknown"), "lastUpdated": end_date, "source": "Advertising Cache"},
        ],
        "conversation": {
            "placeholder": True,
            "prompt": "Advisor fast mode is active. Conversation remains a placeholder until deeper AI integration is added.",
            "history": [],
        },
        "insights": [
            {
                "id": "advisor-fast-insight-1",
                "title": safe_text((executive.get("executive_brief") or {}).get("title"), "Advisor fast insight"),
                "summary": safe_text((executive.get("business_health") or {}).get("summary"), "Advisor cache summary is not ready yet."),
                "tone": "watch",
            }
        ],
        "lastUpdated": end_date,
    }
