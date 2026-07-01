# RBAC Architecture

VOOGLII now uses a centralized RBAC scaffold for platform access.

## Roles

- `owner`
- `admin`
- `manager`
- `analyst`
- `viewer`

## Permissions

- `dashboard:view`
- `reports:view`
- `analytics:view`
- `ads:view`
- `finance:view`
- `users:view`
- `users:manage`
- `settings:manage`

## Backend Integration

- Role-to-permission mapping lives in `analytics/rbac.py`.
- Current actor resolution uses `X-VOOGLII-Actor-Id` as a temporary integration point until real auth/session middleware is connected.
- If the header is absent, the backend falls back to the default owner actor so existing dev flows keep working.
- Access control is enforced through `require_permission(...)` and `require_role(...)`.
- Audit hooks record:
  - role changes
  - user enable/disable actions
  - denied access attempts

## Frontend Integration

- Frontend permission helpers live in `frontend/features/auth/rbac.ts`.
- Sidebar and settings navigation filter items by permissions.
- Team management uses backend APIs and gracefully degrades when the user lacks permission.

## Current Scope

- User directory is currently an in-memory scaffold to avoid changing production auth and deploy flows.
- This keeps the integration surface clear while avoiding fake business analytics payloads.
- A future iteration can replace actor resolution and user storage with real session-backed identity and persistent storage without changing page-level permission checks.
