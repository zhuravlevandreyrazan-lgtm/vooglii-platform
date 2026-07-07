from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

import config
from db_manager import init_db
from vooglii_finance.unified_snapshot import build_unified_financial_snapshot_dict

from .models import ValidationMetricResult, ValidationResult, WBWeeklyReference
from .report_builder import build_validation_report_text
from .root_cause import infer_root_cause


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

METRIC_MAP = {
    "revenue": {"wb_field": "revenue", "vooglii_field": "sales_revenue", "tolerance": 1.0},
    "payout": {"wb_field": "payout", "vooglii_field": "wb_payout", "tolerance": 1.0},
    "logistics": {"wb_field": "logistics", "vooglii_field": "logistics", "tolerance": 1.0},
    "storage": {"wb_field": "storage", "vooglii_field": "storage", "tolerance": 1.0},
    "acquiring": {"wb_field": "acquiring", "vooglii_field": "acquiring", "tolerance": 1.0},
    "wb_deductions": {"wb_field": "wb_deductions", "vooglii_field": "wb_deductions", "tolerance": 1.0},
    "other_expenses": {"wb_field": "other_expenses", "vooglii_field": "other_expenses", "tolerance": 1.0},
    "penalties": {"wb_field": "penalties", "vooglii_field": "penalties", "tolerance": 1.0},
    "advertising": {"wb_field": "advertising", "vooglii_field": "advertising_spend", "tolerance": 1.0},
    "orders_count": {"wb_field": "orders_count", "vooglii_field": "orders_count", "tolerance": 0.0},
    "buyouts_count": {"wb_field": "buyouts_count", "vooglii_field": "buyouts_count", "tolerance": 0.0},
    "returns_count": {"wb_field": "returns_count", "vooglii_field": "returns_count", "tolerance": 0.0},
}


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(config.DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _round_money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def build_vooglii_validation_snapshot(user_id: int, period_from: date, period_to: date) -> dict[str, Any]:
    return build_unified_financial_snapshot_dict(int(user_id), (str(period_from), str(period_to)))


def _metric_status(wb_value: Any, vooglii_value: Any, tolerance: float, snapshot: dict[str, Any]) -> tuple[str, float | None]:
    if wb_value is None or vooglii_value is None:
        return INSUFFICIENT_DATA, None
    delta = round(abs(float(vooglii_value) - float(wb_value)), 2)
    if delta <= float(tolerance):
        return PASS, delta
    if str(snapshot.get("finance_confidence") or "").upper() == "LOW":
        return WARN, delta
    return FAIL, delta


def validate_weekly_report(user_id: int, reference: WBWeeklyReference) -> ValidationResult:
    snapshot = build_vooglii_validation_snapshot(int(user_id), reference.period_from, reference.period_to)
    metrics: list[ValidationMetricResult] = []
    warnings = list(dict.fromkeys([str(item) for item in list(snapshot.get("warnings") or []) if str(item).strip()]))
    for metric_name, mapping in METRIC_MAP.items():
        wb_value = getattr(reference, str(mapping["wb_field"]))
        vooglii_value = snapshot.get(str(mapping["vooglii_field"]))
        tolerance = float(mapping["tolerance"])
        status, delta = _metric_status(wb_value, vooglii_value, tolerance, snapshot)
        root_cause = None if status == PASS else infer_root_cause(metric_name, wb_value, vooglii_value, snapshot)
        metrics.append(
            ValidationMetricResult(
                metric=metric_name,
                wb_value=wb_value,
                vooglii_value=vooglii_value,
                delta=delta,
                tolerance=tolerance,
                status=status,
                source=str(mapping["vooglii_field"]),
                root_cause=root_cause,
            )
        )
        if status == WARN:
            warnings.append(f"{metric_name}: {root_cause or 'warning'}")
    comparable = [item for item in metrics if item.status != INSUFFICIENT_DATA]
    passed = [item for item in comparable if item.status == PASS]
    failed_metrics = [item.metric for item in metrics if item.status == FAIL]
    parity_score = round((len(passed) / len(comparable) * 100) if comparable else 0.0, 1)
    if not comparable:
        overall_status = INSUFFICIENT_DATA
    elif failed_metrics:
        overall_status = FAIL
    elif any(item.status == WARN for item in metrics) or warnings:
        overall_status = WARN
    else:
        overall_status = PASS
    result = ValidationResult(
        user_id=int(user_id),
        period_from=reference.period_from,
        period_to=reference.period_to,
        reference_hash=reference.source_hash,
        parity_score=parity_score,
        metrics=metrics,
        failed_metrics=failed_metrics,
        warnings=list(dict.fromkeys(warnings)),
        status=overall_status,
    )
    save_validation_result(reference, result)
    return result


def save_validation_result(reference: WBWeeklyReference, result: ValidationResult) -> None:
    report_text = build_validation_report_text(result)
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO financial_validation_history(
                user_id, period_from, period_to, reference_hash, reference_file,
                parity_score, status, failed_metrics, warnings, report_text, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(result.user_id),
                str(result.period_from),
                str(result.period_to),
                str(result.reference_hash),
                str(reference.source_file),
                float(result.parity_score),
                str(result.status),
                json.dumps(list(result.failed_metrics), ensure_ascii=False),
                json.dumps(list(result.warnings), ensure_ascii=False),
                report_text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _parse_json_list(raw: Any) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except Exception:
        return [text]
    return [str(item) for item in payload] if isinstance(payload, list) else [str(payload)]


def list_validation_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM financial_validation_history
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["failed_metrics"] = _parse_json_list(item.get("failed_metrics"))
            item["warnings"] = _parse_json_list(item.get("warnings"))
            result.append(item)
        return result
    finally:
        conn.close()


def get_latest_validation_result(user_id: int) -> dict[str, Any] | None:
    rows = list_validation_history(int(user_id), limit=1)
    return rows[0] if rows else None
