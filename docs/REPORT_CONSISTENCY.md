# Report Consistency

## Goal

For the same period, all customer-facing financial screens must display the same financial core values.

Covered screens:

- `/report`
- `/finance`
- `/pnl`
- `/dashboard`
- `/ceo`
- `/business`
- `/advisor`
- `/system`

## Source Of Truth

Use only `build_unified_financial_snapshot(...)` from `vooglii_finance/unified_snapshot.py`.

Renderers may format values, but they may not calculate:

- `profit = revenue - expenses`
- `expenses_total = ...`
- `margin = ...`
- `roi = ...`
- `drr = ...`

## What Must Match

For the same period, the following must be consistent across screens:

- revenue
- payout
- payments received
- advertising spend
- cost price
- logistics
- storage
- acquiring
- WB deductions
- other expenses
- total expenses
- profit before tax
- net profit
- finance status
- confidence status
- cost status

## Runtime Equality Audit

Existing runtime suites verify that real registered handlers still route through the same financial core.

Important checks:

- `tests/test_report_consistency.py`
- `tests/test_rc2_unified_business_views.py`
- `tests/test_june_2026_financial_consistency.py`
- `tests/test_financial_core_integrity.py`
- `tests/test_financial_core_periods.py`

## Safety Rules

- negative unknown WB residual must not be shown as a customer expense
- `reconciliation_delta` must not be added into `expenses_total`
- `LOW` or `UNKNOWN` confidence must not show final profit, margin, or ROI
- false `0.00 ₽` values must not be invented for unavailable finance fields
