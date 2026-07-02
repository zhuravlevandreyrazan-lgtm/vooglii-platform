# Deployment

## Goal

Run VOOGLII Platform on a VPS or cloud host with:

```bash
docker compose up -d
```

## Included

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `.dockerignore`

## Default Services

- `backend`: FastAPI served by `gunicorn` with `uvicorn` workers
- `frontend`: Next.js production standalone build
- `telegram-bot`: Telegram polling worker running `telegram_bot.py` in a separate container

## Future-Ready Profiles

- `postgres`
- `redis`
- `worker`
- `scheduler`

These are scaffolded for future integration and are not required for the current RC deployment.

## Basic Flow

1. Copy `.env.production.example` to your real deployment env file.
2. Replace placeholder secrets and origins.
3. Set `BOT_TOKEN` only in `.env.production`; do not commit the real token.
4. Run `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
5. Check `/api/health`, `/api/version`, `/api/status`, and `/settings/readiness`

## Telegram Bot Deploy

Use the same production stack and shared SQLite volume:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build telegram-bot
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d telegram-bot
docker ps
docker logs vooglii-platform-telegram-bot-1 --tail=100
```

The bot container mounts `/app/storage`, so it works with the same `storage/wildberries.db` as the backend API.

## Notes

- Demo mode remains separated from live mode.
- Existing business logic and analytics formulas are unchanged.
- Persistent storage directories are mounted as Docker volumes for `exports`, `backup`, `restore`, and `storage`.
- `telegram-bot` uses the same backend image and analytics modules as the API container.
