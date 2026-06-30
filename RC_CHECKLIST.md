# RC Checklist

## Product

- Verify routes load: `/`, `/executive`, `/business`, `/finance`, `/advertising`, `/products`, `/inventory`, `/advisor`, `/reports`, `/automation`, `/notifications`, `/settings`, `/settings/profile`, `/settings/wb-cabinet`, `/settings/readiness`, `/demo`.
- Verify SKU drilldowns load from both products and inventory flows.
- Verify Demo Mode badge and DEV Live/Demo toggle behavior.
- Verify Readiness page shows version, build, commit, and backend mode.

## Backend

- Run `python -m py_compile api_server.py telegram_bot.py analytics\*.py scripts\smoke_api.py`
- Run `python scripts/smoke_api.py`

## Frontend

- Run `cd frontend`
- Run `npm.cmd run type-check`
- Run `npm.cmd run build`

## Manual UX Checks

- Confirm top navigation renders without broken badges or empty user/org states.
- Confirm notifications badge loads without opening the full notifications workspace payload on each page.
- Confirm Advisor response, evidence, and links remain readable in both live and demo mode.
- Confirm demo and live pages render acceptable loading, empty, and fallback states.
