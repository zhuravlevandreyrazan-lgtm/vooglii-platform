# Telegram Bot Release Checklist

## Core Checks

- verify `BOT_TOKEN`
- verify `VOOGLII_TOKEN_ENCRYPTION_KEY`
- verify `APP_ENV`
- verify `DB_DIR`
- verify customer-facing texts do not expose developer-only vocabulary

## Financial Core 2.0 Gate

Before release, all of the following must pass:

- `python -m pytest`
- `python scripts/release_check.py`
- `python scripts/diagnose_financial_period.py --user-id 658486226 --from 2026-05-01 --to 2026-05-31 --explain`
- `python scripts/diagnose_financial_period.py --user-id 658486226 --from 2026-06-01 --to 2026-06-30 --explain`
- `python scripts/diagnose_financial_period.py --user-id 658486226 --from 2026-07-01 --to 2026-07-31 --explain`

## Required Financial Tests

- `tests/test_report_consistency.py`
- `tests/test_finance_confidence_layer.py`
- `tests/test_june_2026_financial_consistency.py`
- `tests/test_unified_snapshot_may_restored_values.py`
- `tests/test_financial_core_integrity.py`
- `tests/test_financial_core_periods.py`

## Release Must Fail If

- a renderer recalculates profit or expenses independently
- `/report`, `/finance`, and `/pnl` diverge for the same period
- finance status differs between customer screens
- negative unknown expenses are shown as customer-facing expenses
- `LOW` confidence still shows final profit, margin, or ROI
- key `source_map` entries are empty

## Customer UX Guardrails

- `/finance` explains when data is preliminary
- `/report` does not duplicate financial summary lines
- `/pnl` does not show final profit while confidence is low
- `/system` remains customer-safe for non-developer roles
