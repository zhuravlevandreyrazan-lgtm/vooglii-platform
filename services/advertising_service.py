from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

import config
from load_sales import normalize_advertising_status


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_meta(raw_value: Any) -> dict[str, Any]:
    text = str(raw_value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _date_range_days(date_from: str, date_to: str) -> list[str]:
    start_dt = datetime.strptime(str(date_from), "%Y-%m-%d")
    end_dt = datetime.strptime(str(date_to), "%Y-%m-%d")
    days: list[str] = []
    current = start_dt
    while current <= end_dt:
        days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days


def get_persisted_advertising_sync(user_id: int, db_path: str | None = None) -> dict[str, Any]:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT status, status_reason, last_success_at, next_allowed_at, rows_inserted, source_rows, meta_json
            FROM sync_state
            WHERE telegram_id=? AND sync_block='advertising'
            """,
            (int(user_id),),
        ).fetchone()
        if not row:
            return {
                "status": "MISSING",
                "status_reason": "sync_state row not found",
                "normalized_status": "ADS_ERROR",
                "meta": {},
            }
        meta = _parse_meta(row["meta_json"])
        raw_status = str(meta.get("status") or row["status_reason"] or row["status"] or "")
        return {
            "status": str(row["status"] or ""),
            "status_reason": str(row["status_reason"] or ""),
            "raw_status": raw_status,
            "normalized_status": normalize_advertising_status(raw_status),
            "last_success_at": row["last_success_at"],
            "next_allowed_at": row["next_allowed_at"],
            "rows_inserted": int(row["rows_inserted"] or 0),
            "source_rows": int(row["source_rows"] or 0),
            "meta": meta,
        }
    finally:
        conn.close()


def summarize_advertising_period(user_id: int, date_from: str, date_to: str, db_path: str | None = None) -> dict[str, Any]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT
                CAST(campaign_id AS TEXT) AS campaign_id,
                COUNT(*) AS rows_count,
                ROUND(COALESCE(SUM(spend),0),2) AS spend_total,
                COUNT(DISTINCT substr(advert_date,1,10)) AS days_count
            FROM advertising
            WHERE telegram_id=?
              AND substr(advert_date,1,10) BETWEEN ? AND ?
            GROUP BY CAST(campaign_id AS TEXT)
            ORDER BY CAST(campaign_id AS TEXT)
            """,
            (int(user_id), str(date_from), str(date_to)),
        ).fetchall()
        day_rows = conn.execute(
            """
            SELECT DISTINCT substr(advert_date,1,10) AS advert_day
            FROM advertising
            WHERE telegram_id=?
              AND substr(advert_date,1,10) BETWEEN ? AND ?
            ORDER BY advert_day
            """,
            (int(user_id), str(date_from), str(date_to)),
        ).fetchall()
    finally:
        conn.close()
    requested_days = _date_range_days(date_from, date_to)
    covered_days = [str(row["advert_day"]) for row in day_rows if row["advert_day"]]
    missing_days = [day for day in requested_days if day not in set(covered_days)]
    by_campaign: dict[str, dict[str, Any]] = {}
    for row in rows:
        campaign_id = str(row["campaign_id"] or "")
        if not campaign_id:
            continue
        by_campaign[campaign_id] = {
            "rows_count": int(row["rows_count"] or 0),
            "spend_total": round(float(row["spend_total"] or 0), 2),
            "days_count": int(row["days_count"] or 0),
        }
    total_spend = round(sum(item["spend_total"] for item in by_campaign.values()), 2)
    return {
        "date_from": str(date_from),
        "date_to": str(date_to),
        "campaigns": by_campaign,
        "rows_total": sum(item["rows_count"] for item in by_campaign.values()),
        "campaigns_total": len(by_campaign),
        "total_spend": total_spend,
        "covered_days": covered_days,
        "missing_days": missing_days,
        "coverage_percent": round((len(covered_days) / len(requested_days) * 100) if requested_days else 0, 1),
    }


def evaluate_advertising_sync_audit(user_id: int, report_from: str, report_to: str, db_path: str | None = None) -> dict[str, Any]:
    sync_state = get_persisted_advertising_sync(int(user_id), db_path=db_path)
    meta = dict(sync_state.get("meta") or {})
    period = summarize_advertising_period(int(user_id), str(report_from), str(report_to), db_path=db_path)

    promotion_ids = [str(item) for item in list(meta.get("promotion_count_campaign_ids") or []) if str(item)]
    requested_ids = [str(item) for item in list(meta.get("fullstats_requested_ids") or []) if str(item)]
    returned_ids = [str(item) for item in list(meta.get("fullstats_returned_ids") or []) if str(item)]
    missing_ids = [str(item) for item in list(meta.get("missing_advert_ids") or []) if str(item)]

    local_campaigns = dict(period.get("campaigns") or {})
    spend_by_campaign = {campaign_id: round(float(item.get("spend_total") or 0), 2) for campaign_id, item in local_campaigns.items()}
    rows_by_campaign = {campaign_id: int(item.get("rows_count") or 0) for campaign_id, item in local_campaigns.items()}
    days_by_campaign = {campaign_id: int(item.get("days_count") or 0) for campaign_id, item in local_campaigns.items()}

    missing_with_local_rows = [campaign_id for campaign_id in missing_ids if rows_by_campaign.get(campaign_id, 0) > 0]
    missing_without_local_rows = [campaign_id for campaign_id in missing_ids if rows_by_campaign.get(campaign_id, 0) <= 0]

    raw_normalized = str(sync_state.get("normalized_status") or "")
    report_complete = bool(period.get("rows_total")) and not list(period.get("missing_days") or [])

    if raw_normalized == "ADS_API_LIMIT" and not report_complete:
        customer_status = "ADS_API_LIMIT"
        final_reason = "api_cooldown_and_report_period_incomplete"
        coverage_status = "report_period_incomplete"
    elif raw_normalized == "ADS_NO_CAMPAIGNS" and float(period.get("total_spend") or 0) <= 0:
        customer_status = "ADS_NO_CAMPAIGNS"
        final_reason = "no_campaigns_in_sync_and_no_local_spend"
        coverage_status = "no_campaigns"
    elif report_complete and raw_normalized in {"ADS_PARTIAL", "ADS_OK"}:
        customer_status = "ADS_OK"
        final_reason = (
            "report_period_complete_local_coverage_overrides_broad_lookback_partial"
            if missing_ids
            else "report_period_complete"
        )
        coverage_status = "report_period_complete"
    elif missing_without_local_rows:
        customer_status = "ADS_PARTIAL"
        final_reason = "missing_campaigns_with_unknown_report_period_impact"
        coverage_status = "missing_unknown_campaigns"
    elif missing_with_local_rows:
        customer_status = "ADS_PARTIAL"
        final_reason = "missing_campaigns_with_positive_or_existing_local_spend"
        coverage_status = "missing_spend_campaigns"
    elif float(period.get("total_spend") or 0) > 0:
        customer_status = "ADS_OK"
        final_reason = "local_spend_present_without_active_missing_campaigns"
        coverage_status = "report_period_complete" if report_complete else "local_spend_present_partial_days"
    else:
        customer_status = raw_normalized or "ADS_ERROR"
        final_reason = "fell_back_to_raw_sync_status"
        coverage_status = "insufficient_data"

    return {
        "user_id": int(user_id),
        "requested_report_period": {"date_from": str(report_from), "date_to": str(report_to)},
        "sync_lookback_period": {
            "date_from": meta.get("period_begin"),
            "date_to": meta.get("period_end"),
        },
        "raw_status": sync_state.get("raw_status"),
        "raw_normalized_status": raw_normalized,
        "promotion_count_campaign_ids": promotion_ids,
        "fullstats_requested_ids": requested_ids,
        "fullstats_returned_ids": returned_ids,
        "missing_ids": missing_ids,
        "campaigns_total": len(requested_ids or promotion_ids),
        "campaigns_returned": len(returned_ids),
        "campaigns_missing": len(missing_ids),
        "local_rows_by_campaign": rows_by_campaign,
        "spend_by_campaign": spend_by_campaign,
        "days_by_campaign": days_by_campaign,
        "missing_campaigns_with_local_rows": missing_with_local_rows,
        "missing_campaigns_without_local_rows": missing_without_local_rows,
        "report_period_rows_total": int(period.get("rows_total") or 0),
        "report_period_total_spend": round(float(period.get("total_spend") or 0), 2),
        "report_period_coverage_percent": float(period.get("coverage_percent") or 0),
        "report_period_missing_days": list(period.get("missing_days") or []),
        "campaign_coverage_status": coverage_status,
        "final_ads_status": customer_status,
        "final_ads_reason": final_reason,
    }
