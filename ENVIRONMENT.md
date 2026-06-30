# Environment

## Example Files

- `.env.example`
- `.env.development.example`
- `.env.production.example`
- `frontend/.env.example`

## Variable Groups

- Backend
- Frontend
- Telegram
- Wildberries
- Production
- Demo
- Logging
- Security
- Timeouts

## Startup Validation

Backend startup validates:

- `VERSION`
- environment readiness
- required directories
- writable runtime directories
- build metadata presence

In production, missing required environment values are surfaced through startup validation and health surfaces.
