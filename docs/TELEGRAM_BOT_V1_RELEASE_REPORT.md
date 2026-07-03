# TELEGRAM BOT V1 RELEASE REPORT

## Completed

- Customer brand is unified as `VOOGLII` and `VOOGLII Terminal`.
- `/start` uses the UX 2.0 start screen from `vooglii_telegram/ux/screens.py`.
- Customer `/system` is separated from the engineering audit surface.
- Customer `/advisor` now opens the V2 advisor flow by default.
- Runtime smoke checks cover real registered command handlers.

## VOOGLII Terminal v1.0 RC

- `/home` builds recommendations from runtime state instead of static prompts.
- `/finance` explains when WB has not yet published official finance data.
- `/products` includes concrete SKU risk summaries.
- `/system` shows customer-safe platform health and next steps.

## Runtime Checks Added

- `tests/test_telegram_customer_ux.py`
- `tests/test_telegram_customer_ux_v2.py`
- `tests/test_telegram_start_runtime_smoke.py`
- `tests/test_telegram_runtime_handler_audit.py`
- `scripts/release_check.py`

## Manual Verification

- Open `/start`, `/home`, `/business`, `/finance`, `/products`, `/system`, `/profile`, `/advisor`.
- Confirm no customer output contains `Wildberries Agent`, `current_month`, `last_7_days`, `last_30_days`, `Release Candidate`, `UI Spec`, `Product readiness`.
- Confirm developer-only diagnostics remain hidden from customer roles.

## Known Limits

- `telegram_bot.py` is still a large monolith.
- Docker-based checks require a local Docker runtime.
- `scripts/check_telegram_bot_health.py` requires a configured `BOT_TOKEN`.
