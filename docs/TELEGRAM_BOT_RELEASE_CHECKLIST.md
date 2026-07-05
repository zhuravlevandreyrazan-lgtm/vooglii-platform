# TELEGRAM BOT RELEASE CHECKLIST

## Before Release

- Verify `BOT_TOKEN`.
- Verify `VOOGLII_TOKEN_ENCRYPTION_KEY`.
- Verify `APP_ENV`.
- Verify `DB_DIR`.
- Verify customer help/menu do not expose developer or admin commands.
- Verify customer-facing texts do not contain `Wildberries Agent`, `UNKNOWN`, `NOT_ACTIVE`, `current_month`, `last_7_days`, `last_30_days`.

## Verification Commands

- `python -m pytest`
- `python scripts/release_check.py`
- `python scripts/check_telegram_bot_health.py`
- `python -m py_compile telegram_bot.py vooglii_telegram/ux/*.py`
- `docker compose config`
- `docker compose build`
- `docker compose up -d`
- `docker compose logs telegram-bot`

## Production Readiness

- `/start` begins with `🏢 VOOGLII Terminal`.
- `/menu`, `/home`, `/business`, `/finance`, `/products`, `/advisor`, `/profile`, `/system` use customer UX.
- Customer `/system` does not show engineering diagnostics.
- Developer `/system audit` remains available only for developer/admin roles.
- `/advisor` opens the V2 advisor flow by default.

## Runtime Audit

- Run `tests/test_telegram_start_runtime_smoke.py`.
- Run `tests/test_telegram_runtime_handler_audit.py`.
- Release check must fail if a real registered `CommandHandler` returns legacy UX.

## VOOGLII Terminal v1.0 RC

- Runtime audit verifies real registered handlers, not only helper renderers.
- Customer `/system` is dynamic and role-aware.
- Customer `/home` actions are generated from current business state.
- Customer `/finance` explains why profit may still be unavailable.
- Customer `/products` shows concrete SKU risk summaries.

## Telegram Bot Safe Decomposition v1

- Verify `vooglii_telegram/app.py` and `vooglii_telegram/registry.py` compile successfully.
- Verify `vooglii_telegram/handlers/*.py` compile successfully.
- Verify runtime audits still pass after bootstrap extraction.
- Verify Docker startup stays on `python -u telegram_bot.py`.
# Telegram Bot Release Checklist

## Financial Consistency

- `tests/test_report_consistency.py` passes
- `/business` and `/finance` show the same finance status for the same period
- `/finance` and `/pnl` show the same ad spend / cost price / profit model
- `/advert` and `/finance` show the same advertising spend
- customer screens do not show false `0 ₽` for unavailable financial fields

## Customer UX Guardrails

- `/admin` is blocked for non-admin / non-developer users
- `/stocks` hides technical status for customer roles
- `/system` shows customer-safe financial status text

## Release Commands

- `python -m pytest`
- `python scripts/release_check.py`
- `python -m py_compile telegram_bot.py vooglii_telegram/**/*.py vooglii_finance/**/*.py`
