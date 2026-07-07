from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class WBWeeklyReference:
    source_file: str
    source_hash: str
    period_from: date
    period_to: date
    report_number: str | None
    revenue: float | None
    payout: float | None
    logistics: float | None
    storage: float | None
    acquiring: float | None
    wb_deductions: float | None
    other_expenses: float | None
    penalties: float | None
    advertising: float | None
    orders_count: int | None
    buyouts_count: int | None
    returns_count: int | None
    raw_totals: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationMetricResult:
    metric: str
    wb_value: float | int | None
    vooglii_value: float | int | None
    delta: float | None
    tolerance: float
    status: str
    source: str
    root_cause: str | None


@dataclass
class ValidationResult:
    user_id: int
    period_from: date
    period_to: date
    reference_hash: str
    parity_score: float
    metrics: list[ValidationMetricResult]
    failed_metrics: list[str]
    warnings: list[str]
    status: str
