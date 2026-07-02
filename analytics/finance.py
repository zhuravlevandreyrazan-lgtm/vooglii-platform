from __future__ import annotations

from typing import Any

import telegram_bot

from analytics.common import DEFAULT_USER_ID, current_month_days, safe_float, safe_int, safe_list, safe_text, snapshot_context, status_to_severity, status_to_tone


def _metric(key: str, label: str, value: str, note: str, tone: str) -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "note": note, "tone": tone}


def get_finance_payload(user_id: int = DEFAULT_USER_ID) -> dict[str, Any]:
    start_date, end_date = current_month_days()
    context = snapshot_context()
    engine = telegram_bot._financial_engine_snapshot(start_date, end_date, user=user_id, context=context)
    health = telegram_bot.get_finance_difference_snapshot(user_id, start_date, end_date, context=context)
    business_metrics = telegram_bot._business_metrics_snapshot(user_id, start_date, end_date, context=context)

    operating_profit = safe_float(business_metrics.get("operational_net_profit"))
    official_profit = safe_float(engine.get("official_net_profit"))
    difference = safe_float(health.get("wb_difference"))
    trust_score = safe_int(health.get("trust_score"), 0)
    coverage = safe_float(engine.get("cost_coverage_percent"))
    revenue_base = safe_float(health.get("revenue"))
    explained_total = safe_float(health.get("explained_total"))
    engine_status = safe_text(engine.get("status"), "Unknown")
    no_finance_data = (
        operating_profit is None
        and official_profit is None
        and (difference is None or difference == 0.0)
        and (coverage is None or coverage == 0.0)
        and (revenue_base is None or revenue_base == 0.0)
        and (explained_total is None or explained_total == 0.0)
        and engine_status.upper() == "UNAVAILABLE"
    )
    if no_finance_data:
        difference = None
        coverage = None
        trust_score = None
    health_status = "No finance data available" if no_finance_data else safe_text(health.get("status") or engine.get("status"), "Unknown")
    confidence = "Unavailable" if no_finance_data else ("Low" if (trust_score or 0) < 60 else ("Medium" if (trust_score or 0) < 85 else "High"))

    metrics = [
        _metric("operatingProfit", "Operating Profit", str(operating_profit if operating_profit is not None else "Unavailable"), "Operational management profit from current analytics.", "healthy"),
        _metric("officialProfit", "Official Profit", str(official_profit if official_profit is not None else "Unavailable"), "Official finance profit from Finance API layer.", status_to_tone(engine.get("status"))),
        _metric("profitDifference", "Profit Difference", str(difference if difference is not None else "Unavailable"), "Difference between revenue and payout-side explanation.", "watch"),
        _metric("financeHealth", "Finance Health", safe_text(health_status), "Finance model status from current engine.", status_to_tone(health_status)),
        _metric("trustScore", "Trust Score", f"{trust_score}/100" if trust_score is not None else "Unavailable", "Trust score from profit audit and reconciliation.", "risk" if (trust_score or 0) < 60 else "watch"),
        _metric("coverage", "Coverage", f"{coverage}%" if coverage is not None else "Unavailable", "Cost and finance coverage available for reconciliation.", "accent"),
        _metric("confidence", "Confidence", confidence, "Confidence inherited from trust and finance status.", status_to_tone(confidence)),
        _metric("residualModel", "Residual Model", safe_text(health.get("bridge_mode"), "Informational only"), "Residual bridge usage status.", "neutral"),
        _metric(
            "income",
            "Income",
            str(revenue_base) if revenue_base is not None and not no_finance_data else "Unavailable",
            "Revenue base for the selected period.",
            "healthy",
        ),
        _metric(
            "expenses",
            "Expenses",
            str(explained_total) if explained_total is not None and not no_finance_data else "Unavailable",
            "Explained payout-side components.",
            "watch",
        ),
    ]

    warnings = safe_list(engine.get("warnings")) + safe_list(health.get("warnings"))
    alerts = [
        {
            "id": f"finance-alert-{index}",
            "title": "Finance alert",
            "description": item,
            "severity": status_to_severity(health_status),
            "source": "backend",
        }
        for index, item in enumerate(warnings[:5], 1)
    ]

    timeline = [
        {
            "id": "finance-timeline-1",
            "title": "Latest finance snapshot updated",
            "description": f"Finance engine status: {safe_text(engine.get('status'), 'Unknown')}.",
            "period": "latest",
            "severity": status_to_severity(engine.get("status")),
            "source": "backend",
        },
        {
            "id": "finance-timeline-2",
            "title": "Latest reconciliation evaluated",
            "description": safe_text(health.get("reason") or health.get("reconciliation_status"), "Finance reconciliation updated."),
            "period": "audit",
            "severity": status_to_severity(health.get("status")),
            "source": "backend",
        },
    ]

    return {
        "summary": {
            "operatingProfit": operating_profit,
            "officialProfit": official_profit,
            "difference": difference,
            "health": health_status,
            "trustScore": trust_score,
            "status": "No finance data available" if no_finance_data else safe_text(health.get("status"), "Pending"),
        },
        "quality": {
            "coverage": coverage,
            "residualUsage": safe_text(health.get("bridge_mode"), "No residual usage detail available."),
            "trustScore": trust_score,
            "confidence": confidence,
            "health": health_status,
        },
        "difference": {
            "operatingProfit": operating_profit,
            "officialProfit": official_profit,
            "difference": difference,
            "differencePercent": None if no_finance_data else safe_float(health.get("explained_percent")),
            "reason": safe_text(health.get("reason"), "Difference explanation is not available from backend yet."),
            "explanation": safe_text(health.get("recommended_profit_base"), ""),
        },
        "metrics": metrics,
        "alerts": alerts,
        "timeline": timeline,
        "lastUpdated": end_date,
    }
