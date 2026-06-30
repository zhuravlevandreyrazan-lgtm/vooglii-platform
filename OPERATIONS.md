# Operations

## Core Checks

- `GET /api/health`
- `GET /api/metrics`
- `GET /api/status`
- `GET /api/version`
- `GET /api/workspace/context`

## Routine Validation

- Run `python scripts/smoke_api.py`
- Run `npm.cmd run type-check`
- Run `npm.cmd run build`

## Runtime Areas

- API
- Runtime
- Analytics
- Advisor
- Automation
- Notifications
- Authentication
- Workspace Context
- Errors
- Warnings

## Incident Handling

- Use `/api/health` for liveness and build environment checks.
- Use `/api/metrics` for startup validation and lightweight runtime metrics.
- Use `/settings/readiness` for operator-facing release/deployment visibility.
