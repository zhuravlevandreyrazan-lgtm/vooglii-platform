# Multi-Tenant Architecture

## Goal

Prepare VOOGLII Platform for multi-organization and multi-cabinet operation without changing analytics formulas, Telegram Agent behavior, or existing workspace routes.

## Hierarchy

User

↓

Organization

↓

Wildberries Cabinets

↓

Workspace Context

↓

Analytics Workspaces

## Current RC Scope

- One authenticated user can switch between multiple organizations.
- Each organization can expose multiple WB cabinets.
- Active organization and active cabinet are stored in a safe in-memory backend registry for dev/demo.
- Frontend keeps a shared workspace context so switching happens without page reload.
- Existing workspaces are context-aware even when backend analytics payloads are not yet filtered by tenant.

## Backend

- `GET /api/organizations`
- `GET /api/organizations/{id}`
- `POST /api/organizations/select`
- `GET /api/wb-cabinets`
- `GET /api/wb-cabinets/{id}`
- `POST /api/wb-cabinets/select`
- `GET /api/workspace/context`

The backend registry provides:

- active organization id
- active cabinet id
- last changed timestamp
- scoped dev/demo metadata for auth, automation, and notifications payloads

## Frontend

Shared context lives in:

- `frontend/shared/workspace-context/workspace-context.ts`
- `frontend/shared/workspace-context/workspace-context-provider.tsx`
- `frontend/shared/workspace-context/useWorkspaceContext.ts`

The context stores:

- selected organization
- selected cabinet
- current mode
- last changed timestamp
- organization and cabinet lists

## Switching Behavior

- Organization switch updates shared workspace context immediately.
- Cabinet switch updates shared workspace context immediately.
- No `window.location` usage.
- No full page reload.
- Auth shell, top bar, sidebar, Advisor, Product Drilldown, Automation, Notifications, and Readiness react to the new active context.

## Analytics Boundary

Analytics builders are unchanged.

At this stage:

- workspaces display the current organization/cabinet context
- Advisor query includes `organizationId` and `cabinetId`
- automation and notifications records are annotated with tenant scope metadata
- business/finance/products/inventory snapshots are still contract-compatible shared analytics payloads
