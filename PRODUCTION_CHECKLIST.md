# Production Checklist

## Before Deployment

- Fill production environment values from `.env.production.example`
- Verify trusted origins and hosts
- Verify no real tokens are committed
- Verify `/api/health`, `/api/version`, and `/api/status`

## Validation

- `python -m py_compile api_server.py telegram_bot.py analytics\*.py scripts\smoke_api.py`
- `python scripts/smoke_api.py`
- `cd frontend`
- `npm.cmd run type-check`
- `npm.cmd run build`

## Infrastructure

- Build Docker images
- Run `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
- Confirm readiness dashboard values
- Confirm startup validation is green

## Remaining Before True Production

- real secrets management
- reverse proxy / TLS
- persistent DB and Redis activation
- worker and scheduler activation
- backup execution implementation
