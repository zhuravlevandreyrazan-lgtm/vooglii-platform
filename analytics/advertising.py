from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import DEFAULT_USER_ID, current_month_days, safe_float, safe_list, safe_text, snapshot_context, status_to_severity, status_to_tone


def get_advertising_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    ads = telegram_bot._ads_snapshot(user_id, (start_date, end_date), context=context)
    health = telegram_bot.get_advertising_health_snapshot(user_id, start_date, end_date)

    total_spend = safe_float(ads.get("total_spend"))
    linked_spend = safe_float(health.get("linked_spend"))
    unlinked_spend = safe_float(health.get("unlinked_spend"))
    roas = safe_float(ads.get("total_roas"))
    acos = safe_float(ads.get("total_drr"))
    campaigns_data = list(ads.get("campaigns") or [])
    no_advertising_data = (
        not campaigns_data
        and (total_spend is None or total_spend == 0.0)
        and (linked_spend is None or linked_spend == 0.0)
        and (unlinked_spend is None or unlinked_spend == 0.0)
        and roas is None
        and acos is None
    )

    summary = {
        "advertisingSpend": None if no_advertising_data else total_spend,
        "linkedSpend": None if no_advertising_data else linked_spend,
        "unlinkedSpend": None if no_advertising_data else unlinked_spend,
        "roas": None if no_advertising_data else roas,
        "acos": None if no_advertising_data else acos,
        "adsHealth": "No advertising data available" if no_advertising_data else safe_text(health.get("status"), "Unknown"),
        "trust": "Unknown" if no_advertising_data else ("Medium" if safe_float(health.get("linkability_percent"), 0) >= 70 else "Low"),
        "status": "No advertising data available" if no_advertising_data else safe_text(ads.get("main_recommendation"), "No advertising recommendation available"),
    }
    health_block = {
        "adsHealth": summary["adsHealth"],
        "linkability": None if no_advertising_data else safe_float(health.get("linkability_percent")),
        "duplicateSpend": None if no_advertising_data else safe_float(health.get("duplicate_negative_spend")),
        "linkedPercent": None if no_advertising_data else safe_float(health.get("linkability_percent")),
        "coverage": None if no_advertising_data else safe_float(health.get("linkability_percent")),
        "status": safe_text(ads.get("main_recommendation"), "Pending"),
    }
    metrics = [
        {"key": "advertisingSpend", "label": "Advertising Spend", "value": str(summary["advertisingSpend"]) if summary["advertisingSpend"] is not None else "Unavailable", "note": "Total spend from local advertising analytics.", "tone": "watch"},
        {"key": "linkedSpend", "label": "Linked Spend", "value": str(summary["linkedSpend"]) if summary["linkedSpend"] is not None else "Unavailable", "note": "Spend linked to SKU/campaign analytics.", "tone": "healthy"},
        {"key": "unlinkedSpend", "label": "Unlinked Spend", "value": str(summary["unlinkedSpend"]) if summary["unlinkedSpend"] is not None else "Unavailable", "note": "Spend not yet linked to clean advertising rows.", "tone": "watch"},
        {"key": "roas", "label": "ROAS", "value": str(summary["roas"]) if summary["roas"] is not None else "Unavailable", "note": "Advertising return on spend.", "tone": "healthy"},
        {"key": "acos", "label": "ACOS", "value": str(summary["acos"]) if summary["acos"] is not None else "Unavailable", "note": "Advertising cost of sales.", "tone": "accent"},
        {"key": "adsHealth", "label": "Ads Health", "value": summary["adsHealth"], "note": "Status from advertising health snapshot.", "tone": status_to_tone(summary["adsHealth"])},
        {"key": "trust", "label": "Trust", "value": summary["trust"], "note": "Trust derived from linkability quality.", "tone": "neutral"},
        {"key": "status", "label": "Status", "value": summary["status"], "note": "Main advertising recommendation summary.", "tone": "watch"},
    ]
    recommendations = []
    for row in campaigns_data[:5]:
        recommendations.append(
            {
                "id": f"ads-rec-{safe_text(row.get('campaign_id_display'), 'n/a')}",
                "campaign": safe_text(row.get("campaign_name") or row.get("campaign_id_display"), "Unknown campaign"),
                "recommendation": safe_text(row.get("recommendation"), "Review campaign"),
                "reason": safe_text(row.get("reason"), "No reason provided."),
                "expectedEffect": safe_text(row.get("metric"), "No metric detail."),
                "confidence": "Medium",
                "severity": status_to_severity(row.get("decision")),
            }
        )
    alerts = [
        {
            "id": f"ads-alert-{index}",
            "title": "Advertising alert",
            "description": item,
            "severity": status_to_severity(summary["adsHealth"]),
            "source": "backend",
        }
        for index, item in enumerate(safe_list(ads.get("warnings"))[:4], 1)
    ]
    campaigns = [
        {
            "id": f"campaign-{index}",
            "campaign": safe_text(row.get("campaign_name") or row.get("campaign_id_display"), "Unknown"),
            "spend": safe_float(row.get("spend")),
            "revenue": safe_float(row.get("ad_revenue")),
            "roas": safe_float(row.get("roas")),
            "acos": safe_float(row.get("drr")),
            "status": safe_text(row.get("decision"), "Unknown"),
            "recommendation": safe_text(row.get("recommendation"), "Review manually"),
        }
        for index, row in enumerate(campaigns_data, 1)
    ]
    return {
        "summary": summary,
        "health": health_block,
        "metrics": metrics,
        "recommendations": recommendations,
        "alerts": alerts,
        "timeline": [
            {
                "id": "ads-timeline-1",
                "title": "Advertising sync completed",
                "description": "Advertising snapshot has been refreshed from the current analytics engine and campaign data.",
                "period": "sync",
                "severity": status_to_severity(summary["adsHealth"]),
                "source": "backend",
            }
        ],
        "campaigns": campaigns,
        "lastUpdated": end_date,
    }
