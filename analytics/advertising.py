from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import DEFAULT_USER_ID, current_month_days, safe_float, safe_list, safe_text, snapshot_context, status_to_severity, status_to_tone


def get_advertising_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    ads = telegram_bot._ads_snapshot(user_id, (start_date, end_date), context=context)
    health = telegram_bot.get_advertising_health_snapshot(user_id, start_date, end_date)

    summary = {
        "advertisingSpend": safe_float(ads.get("total_spend")),
        "linkedSpend": safe_float(health.get("linked_spend")),
        "unlinkedSpend": safe_float(health.get("unlinked_spend")),
        "roas": safe_float(ads.get("total_roas")),
        "acos": safe_float(ads.get("total_drr")),
        "adsHealth": safe_text(health.get("status"), "Unknown"),
        "trust": "Medium" if safe_float(health.get("linkability_percent"), 0) >= 70 else "Low",
        "status": safe_text(ads.get("main_recommendation"), "Pending"),
    }
    health_block = {
        "adsHealth": summary["adsHealth"],
        "linkability": safe_float(health.get("linkability_percent")),
        "duplicateSpend": safe_float(health.get("duplicate_negative_spend")),
        "linkedPercent": safe_float(health.get("linkability_percent")),
        "coverage": safe_float(health.get("linkability_percent")),
        "status": safe_text(ads.get("main_recommendation"), "Pending"),
    }
    metrics = [
        {"key": "advertisingSpend", "label": "Advertising Spend", "value": str(summary["advertisingSpend"]), "note": "Total spend from local advertising analytics.", "tone": "watch"},
        {"key": "linkedSpend", "label": "Linked Spend", "value": str(summary["linkedSpend"]), "note": "Spend linked to SKU/campaign analytics.", "tone": "healthy"},
        {"key": "unlinkedSpend", "label": "Unlinked Spend", "value": str(summary["unlinkedSpend"]), "note": "Spend not yet linked to clean advertising rows.", "tone": "watch"},
        {"key": "roas", "label": "ROAS", "value": str(summary["roas"]), "note": "Advertising return on spend.", "tone": "healthy"},
        {"key": "acos", "label": "ACOS", "value": str(summary["acos"]), "note": "Advertising cost of sales.", "tone": "accent"},
        {"key": "adsHealth", "label": "Ads Health", "value": summary["adsHealth"], "note": "Status from advertising health snapshot.", "tone": status_to_tone(summary["adsHealth"])},
        {"key": "trust", "label": "Trust", "value": summary["trust"], "note": "Trust derived from linkability quality.", "tone": "neutral"},
        {"key": "status", "label": "Status", "value": summary["status"], "note": "Main advertising recommendation summary.", "tone": "watch"},
    ]
    recommendations = []
    for row in list(ads.get("campaigns") or [])[:5]:
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
        for index, row in enumerate(list(ads.get("campaigns") or []), 1)
    ]
    return {
        "summary": summary,
        "health": health_block,
        "metrics": metrics,
        "recommendations": recommendations,
        "alerts": alerts or [{
            "id": "ads-alert-fallback",
            "title": "No advertising alerts available",
            "description": "Advertising analytics did not return explicit warnings.",
            "severity": "info",
            "source": "placeholder",
        }],
        "timeline": [
            {
                "id": "ads-timeline-1",
                "title": "Advertising sync completed",
                "description": "Advertising snapshot has been refreshed from analytics engine.",
                "period": "sync",
                "severity": status_to_severity(summary["adsHealth"]),
                "source": "backend",
            }
        ],
        "campaigns": campaigns,
        "lastUpdated": end_date,
    }

