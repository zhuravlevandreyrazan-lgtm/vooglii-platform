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

## Future-Ready Profiles

- `postgres`
- `redis`
- `worker`
- `scheduler`

These are scaffolded for future integration and are not required for the current RC deployment.

## Basic Flow

1. Copy `.env.production.example` to your real deployment env file.
2. Replace placeholder secrets and origins.
3. Run `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
4. Check `/api/health`, `/api/version`, `/api/status`, and `/settings/readiness`

## Notes

- Demo mode remains separated from live mode.
- Existing business logic and analytics formulas are unchanged.
- Persistent storage directories are mounted as Docker volumes for `exports`, `backup`, `restore`, and `storage`.
