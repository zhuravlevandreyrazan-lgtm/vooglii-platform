# Report Consistency

## Goal

All customer-facing Telegram screens should show the same financial numbers for the same period.

Covered screens:

- `/business`
- `/finance`
- `/pnl`
- `/report`
- `/dashboard`
- `/ceo`
- `/system`
- `/advert`
- `/adsaudit`
- `/products`

## Source of Truth

Use `vooglii_finance.unified_snapshot.build_unified_financial_snapshot(...)`.

## What Must Match

For the same period, the following values must be consistent:

- advertising spend
- revenue
- payout
- cost price
- total expenses
- profit before tax
- net profit
- margin
- ROI
- finance status
- advertising status
- cost status

## Automated Audit

The repo contains `tests/test_report_consistency.py`.

It checks that:

- finance screens use the same advertising number
- P&L and report screens use the same expense/profit logic
- customer screens do not fall back to false `0 ₽`
- consistency audit reports no mismatches
