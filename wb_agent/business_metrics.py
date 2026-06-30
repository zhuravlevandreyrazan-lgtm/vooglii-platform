"""Pure readonly Business Metrics Engine helpers.

This module aggregates already-built snapshot dicts into one normalized
read-only structure. It must not call APIs, read/write DB, or mutate cache.
"""

from dataclasses import asdict, dataclass, field

from wb_agent.financial_engine import (
    FINANCIAL_ENGINE_AVAILABLE_STATUSES,
    FINANCIAL_ENGINE_RUNTIME_UNAVAILABLE_STATUSES,
)
from wb_agent.formatting import money

BUSINESS_METRICS_OFFICIAL_ALLOWED_STATUSES = (
    *FINANCIAL_ENGINE_AVAILABLE_STATUSES,
    *FINANCIAL_ENGINE_RUNTIME_UNAVAILABLE_STATUSES,
)

__all__ = [
    "BUSINESS_METRICS_OFFICIAL_ALLOWED_STATUSES",
    "BusinessMetricsSnapshot",
    "build_business_metrics_snapshot",
    "build_business_metrics_light_snapshot",
    "business_metrics_text",
]


@dataclass
class BusinessMetricsSnapshot:
    period_start: str
    period_end: str
    source_status: str

    official_available: bool
    official_status: str
    official_source: str | None
    official_wb_payment_total: float | None
    official_cost_total: float | None
    official_tax_amount: float | None
    official_profit_before_tax: float | None
    official_net_profit: float | None
    official_new_finance_available: bool
    legacy_estimate_available: bool
    legacy_financial_profit_estimate: float | None
    official_ads_handling: str | None
    official_warnings: list[str] = field(default_factory=list)

    operational_available: bool = False
    operational_revenue: float | None = None
    operational_for_pay: float | None = None
    operational_ads: float | None = None
    operational_cost: float | None = None
    operational_tax: float | None = None
    operational_profit_before_tax: float | None = None
    operational_net_profit: float | None = None
    operational_warnings: list[str] = field(default_factory=list)

    data_quality_score: float | None = None
    trust_score: int | None = None
    finance_api_status: str | None = None
    advertising_health: str | None = None
    cost_coverage_percent: float | None = None
    missing_cost_skus: list[str] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)


def _float_or_none(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except Exception:
        return None


def _int_or_none(value):
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _list_text(value):
    result = []
    for item in list(value or []):
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _is_may_2026(period_start, period_end):
    return str(period_start) == "2026-05-01" and str(period_end) == "2026-05-31"


def _cost_coverage_display(status, coverage):
    normalized_status = str(status or "UNAVAILABLE")
    if normalized_status == "LEGACY_FALLBACK":
        return f"{float(coverage or 0):.1f}% (legacy)" if coverage is not None else "legacy"
    if normalized_status == "DETAIL_REQUIRED":
        return "DETAIL_REQUIRED"
    if normalized_status in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "API_ENDPOINT_ERROR", "ERROR"):
        return "unavailable"
    if coverage is None:
        return "unavailable"
    return f"{float(coverage):.1f}%"


def build_business_metrics_snapshot(
    period_start,
    period_end,
    financial_engine_snapshot=None,
    operational_profit_snapshot=None,
    data_quality_snapshot=None,
    ads_health_snapshot=None,
):
    period_start = str(period_start)
    period_end = str(period_end)
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    operational_profit_snapshot = dict(operational_profit_snapshot or {})
    data_quality_snapshot = dict(data_quality_snapshot or {})
    ads_health_snapshot = dict(ads_health_snapshot or {})

    official_status = str(financial_engine_snapshot.get("status") or "UNAVAILABLE")
    official_available = official_status in FINANCIAL_ENGINE_AVAILABLE_STATUSES and financial_engine_snapshot.get("official_net_profit") is not None
    legacy_estimate_available = official_status == "LEGACY_FALLBACK" and financial_engine_snapshot.get("legacy_financial_profit_estimate") is not None
    official_warnings = _list_text(financial_engine_snapshot.get("warnings"))

    operational_net_profit = _float_or_none(
        operational_profit_snapshot.get("net_profit_after_tax_from_payout")
        if "net_profit_after_tax_from_payout" in operational_profit_snapshot
        else operational_profit_snapshot.get("net_profit_after_tax")
    )
    operational_available = bool(operational_profit_snapshot) and (
        operational_profit_snapshot.get("revenue") is not None
        or operational_profit_snapshot.get("payout") is not None
        or operational_net_profit is not None
    )
    operational_warnings = _list_text(operational_profit_snapshot.get("warnings"))
    if not official_available and operational_available:
        operational_warnings.append("Operational profit is not official financial profit.")

    notes = []
    if not official_available and _is_may_2026(period_start, period_end):
        notes.append("May 2026 has regression Gold Standard reference, but runtime official profit requires Finance API.")
    if legacy_estimate_available:
        notes.append("legacy fallback mode: finance available for reconciliation, but official new Finance API is unavailable")
    if official_status in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR"):
        notes.append("cost trust unavailable until finance detail rows are available")

    trust_score = _int_or_none(data_quality_snapshot.get("trust_score"))
    if trust_score is None:
        overall_score = _float_or_none(data_quality_snapshot.get("overall_score"))
        trust_score = _int_or_none(overall_score)

    snapshot = BusinessMetricsSnapshot(
        period_start=period_start,
        period_end=period_end,
        source_status="official" if official_available else ("legacy_estimate" if legacy_estimate_available else ("operational_estimate" if operational_available else "unavailable")),
        official_available=bool(official_available),
        official_status=official_status,
        official_source=str(financial_engine_snapshot.get("source") or "unavailable"),
        official_wb_payment_total=_float_or_none(financial_engine_snapshot.get("wb_payment_total")),
        official_cost_total=_float_or_none(financial_engine_snapshot.get("cost_total")),
        official_tax_amount=_float_or_none(financial_engine_snapshot.get("tax_amount")),
        official_profit_before_tax=_float_or_none(financial_engine_snapshot.get("profit_before_tax")),
        official_net_profit=_float_or_none(financial_engine_snapshot.get("official_net_profit")),
        official_new_finance_available=bool(financial_engine_snapshot.get("official_new_finance_available")),
        legacy_estimate_available=bool(financial_engine_snapshot.get("legacy_estimate_available") or legacy_estimate_available),
        legacy_financial_profit_estimate=_float_or_none(financial_engine_snapshot.get("legacy_financial_profit_estimate")),
        official_ads_handling=str(financial_engine_snapshot.get("ads_handling") or "UNKNOWN"),
        official_warnings=official_warnings,
        operational_available=bool(operational_available),
        operational_revenue=_float_or_none(operational_profit_snapshot.get("revenue")),
        operational_for_pay=_float_or_none(
            operational_profit_snapshot.get("payout")
            if "payout" in operational_profit_snapshot
            else operational_profit_snapshot.get("sales_for_pay_total")
        ),
        operational_ads=_float_or_none(
            operational_profit_snapshot.get("advertising")
            if "advertising" in operational_profit_snapshot
            else operational_profit_snapshot.get("ads")
        ),
        operational_cost=_float_or_none(
            operational_profit_snapshot.get("cost_price")
            if "cost_price" in operational_profit_snapshot
            else operational_profit_snapshot.get("cost")
        ),
        operational_tax=_float_or_none(
            operational_profit_snapshot.get("tax_amount")
            if "tax_amount" in operational_profit_snapshot
            else operational_profit_snapshot.get("tax")
        ),
        operational_profit_before_tax=_float_or_none(
            operational_profit_snapshot.get("profit_before_tax_from_payout")
            if "profit_before_tax_from_payout" in operational_profit_snapshot
            else operational_profit_snapshot.get("profit_before_tax")
        ),
        operational_net_profit=operational_net_profit,
        operational_warnings=operational_warnings,
        data_quality_score=_float_or_none(data_quality_snapshot.get("overall_score")),
        trust_score=trust_score,
        finance_api_status=str(financial_engine_snapshot.get("status") or "UNAVAILABLE"),
        advertising_health=str(ads_health_snapshot.get("status") or "UNKNOWN"),
        cost_coverage_percent=_float_or_none(financial_engine_snapshot.get("cost_coverage_percent")),
        missing_cost_skus=_list_text(financial_engine_snapshot.get("missing_cost_skus")),
        notes=notes,
    )
    return asdict(snapshot)


def build_business_metrics_light_snapshot(
    period_start,
    period_end,
    financial_engine_snapshot=None,
    data_quality_snapshot=None,
    ads_health_snapshot=None,
    operational_estimate_available=False,
    operational_warnings=None,
):
    period_start = str(period_start)
    period_end = str(period_end)
    financial_engine_snapshot = dict(financial_engine_snapshot or {})
    data_quality_snapshot = dict(data_quality_snapshot or {})
    ads_health_snapshot = dict(ads_health_snapshot or {})

    official_status = str(financial_engine_snapshot.get("status") or "UNAVAILABLE")
    official_available = (
        official_status in FINANCIAL_ENGINE_AVAILABLE_STATUSES
        and financial_engine_snapshot.get("official_net_profit") is not None
    )
    legacy_estimate_available = official_status == "LEGACY_FALLBACK" and financial_engine_snapshot.get("legacy_financial_profit_estimate") is not None
    official_warnings = _list_text(financial_engine_snapshot.get("warnings"))

    trust_score = _int_or_none(data_quality_snapshot.get("trust_score"))
    if trust_score is None:
        trust_score = _int_or_none(data_quality_snapshot.get("overall_score"))

    notes = []
    if not official_available and _is_may_2026(period_start, period_end):
        notes.append("May 2026 has regression Gold Standard reference, but runtime official profit requires Finance API.")
    if legacy_estimate_available:
        notes.append("legacy fallback mode: finance available for reconciliation, but official new Finance API is unavailable")
    if official_status in ("RATE_LIMIT", "FORBIDDEN", "UNAUTHORIZED", "UNAVAILABLE", "DETAIL_REQUIRED", "API_ENDPOINT_ERROR", "ERROR"):
        notes.append("cost trust unavailable until finance detail rows are available")

    snapshot = BusinessMetricsSnapshot(
        period_start=period_start,
        period_end=period_end,
        source_status="official" if official_available else ("legacy_estimate" if legacy_estimate_available else ("operational_estimate" if operational_estimate_available else "unavailable")),
        official_available=bool(official_available),
        official_status=official_status,
        official_source=str(financial_engine_snapshot.get("source") or "unavailable"),
        official_wb_payment_total=_float_or_none(financial_engine_snapshot.get("wb_payment_total")),
        official_cost_total=_float_or_none(financial_engine_snapshot.get("cost_total")),
        official_tax_amount=_float_or_none(financial_engine_snapshot.get("tax_amount")),
        official_profit_before_tax=_float_or_none(financial_engine_snapshot.get("profit_before_tax")),
        official_net_profit=_float_or_none(financial_engine_snapshot.get("official_net_profit")),
        official_new_finance_available=bool(financial_engine_snapshot.get("official_new_finance_available")),
        legacy_estimate_available=bool(financial_engine_snapshot.get("legacy_estimate_available") or legacy_estimate_available),
        legacy_financial_profit_estimate=_float_or_none(financial_engine_snapshot.get("legacy_financial_profit_estimate")),
        official_ads_handling=str(financial_engine_snapshot.get("ads_handling") or "UNKNOWN"),
        official_warnings=official_warnings,
        operational_available=bool(operational_estimate_available),
        operational_warnings=_list_text(operational_warnings),
        data_quality_score=_float_or_none(data_quality_snapshot.get("overall_score")),
        trust_score=trust_score,
        finance_api_status=official_status,
        advertising_health=str(ads_health_snapshot.get("status") or "UNKNOWN"),
        cost_coverage_percent=_float_or_none(financial_engine_snapshot.get("cost_coverage_percent")),
        missing_cost_skus=_list_text(financial_engine_snapshot.get("missing_cost_skus")),
        notes=notes,
    )
    return asdict(snapshot)


def business_metrics_text(snapshot):
    snapshot = dict(snapshot or {})
    official_available = bool(snapshot.get("official_available"))
    operational_available = bool(snapshot.get("operational_available"))
    legacy_estimate_available = bool(snapshot.get("legacy_estimate_available"))
    official_net_profit = snapshot.get("official_net_profit")
    operational_net_profit = snapshot.get("operational_net_profit")
    legacy_net_profit = snapshot.get("legacy_financial_profit_estimate")

    lines = [
        "BUSINESS METRICS",
        "",
        f'Period: {snapshot.get("period_start") or "-"}..{snapshot.get("period_end") or "-"}',
        "",
        "Official financial profit:",
        f'status: {snapshot.get("official_status") or "UNAVAILABLE"}',
        f'net profit: {money(official_net_profit)}' if official_available and official_net_profit is not None else "net profit: unavailable",
        f'source: {snapshot.get("official_source") or "unavailable"}',
        f'official new finance: {"yes" if snapshot.get("official_new_finance_available") else "no"}',
        f'legacy estimate: {money(legacy_net_profit)}' if legacy_estimate_available and legacy_net_profit is not None else f'legacy estimate: {"yes" if legacy_estimate_available else "no"}',
        "",
        "Operational estimate:",
        f'status: {"AVAILABLE" if operational_available else "UNAVAILABLE"}',
        f'net profit estimate: {money(operational_net_profit)}' if operational_available and operational_net_profit is not None else "net profit estimate: unavailable",
        "warning: not official profit",
        "",
        "Quality:",
        f'trust score: {snapshot.get("trust_score") if snapshot.get("trust_score") is not None else "-"}',
        f'finance api: {snapshot.get("finance_api_status") or "UNKNOWN"}',
        f'ads health: {snapshot.get("advertising_health") or "UNKNOWN"}',
        f'cost coverage: {_cost_coverage_display(snapshot.get("official_status"), snapshot.get("cost_coverage_percent"))}',
    ]
    notes = _list_text(snapshot.get("notes"))
    if notes:
        lines.extend(["", "Notes:"])
        lines.extend([f"- {item}" for item in notes])
    return "\n".join(lines)
