# API Contracts

## Runtime Metadata
- Heavy analytics endpoints return `runtime` metadata:
```json
{
  "runtime": {
    "duration_ms": 184.22,
    "cached": false,
    "stale": false,
    "degraded": false,
    "source": "live"
  }
}
```
- `cached=true`: response came from in-memory TTL cache.
- `stale=true`: live rebuild failed or timed out, and the API returned the most recent stale cache entry.
- `degraded=true`: no usable live or stale snapshot was available, so the API returned a safe fallback payload that still matches the contract.
- `source` values:
  - `live`: snapshot was rebuilt successfully.
  - `cache`: fresh cached snapshot was returned.
  - `stale_cache`: expired cache was returned after a live failure or timeout.
  - `degraded`: safe fallback payload was returned.
  - `dev`: safe dev profile or metadata was returned for auth-oriented endpoints.

## Performance Budgets
- `/api/health`, `/api/status`, `/api/version`: target `<= 500 ms`
- `/api/command-center`, `/api/executive`, `/api/advisor`: target `<= 5 s`
- `/api/advisor/query`: target `<= 5 s`
- `/api/business`, `/api/finance`, `/api/advertising`, `/api/products`, `/api/inventory`: target `<= 10 s`
- `/api/reports`, `/api/system`: target `<= 5 s`

## Timeout And Cache Policy
- Heavy endpoints are wrapped with `run_with_timeout()` and protected from blocking the request indefinitely.
- Timeouts do not change finance, ads, inventory, or business formulas. They only affect response delivery mode.
- Shared in-memory TTL cache is used for heavy snapshots:
  - `executive`: 120 seconds for `/api/command-center` and `/api/executive`
  - `advisor`: 120 seconds
  - `reports`: 120 seconds
  - `system`: 120 seconds
  - `business`, `finance`, `advertising`, `products`, `inventory`: 180 seconds
- `/api/health`, `/api/status`, and `/api/version` never trigger heavy analytics builders.
- `/api/status` reads only lightweight runtime registries: cache state, slow endpoints, last successful snapshots, and last errors.

## Frontend Live And Fallback Semantics
- Production-live primary endpoints:
  - `/api/business`
  - `/api/finance`
  - `/api/advertising`
  - `/api/products`
  - `/api/inventory`
- Degraded-safe endpoints:
  - `/api/command-center`
  - `/api/executive`
  - `/api/advisor`
  - `/api/advisor/query`
  - `/api/reports`
  - `/api/system`
- Stable frontend workspaces use backend responses as the primary source and switch to frontend fallback snapshots only when:
  - the request fails
  - JSON is invalid
  - payload validation fails
  - request timeout happens on the frontend side
- Frontend normalized snapshots may expose:
```json
{
  "diagnostics": {
    "source": "live",
    "degraded": false,
    "cached": false,
    "stale": false,
    "durationMs": 184.22,
    "validationStatus": "ok"
  }
}
```
- In development mode the frontend may render a small runtime badge with `source`, `durationMs`, and `degraded` state.
- Frontend fallback warning text:
  - `Using fallback data. Backend response is unavailable or invalid.`

## GET `/api/health`
- Purpose: basic API liveness.
- Response: `status`, `product`, `mode`, `uptimeSeconds`, `memoryUsageMb`, `pythonVersion`, `applicationVersion`, `environment`, `runtimeMode`, `buildInfo`, `startup`.
- Errors: unified JSON error envelope.

## GET `/api/metrics`
- Purpose: lightweight operational metrics without Prometheus dependency.
- Response: `build`, `uptimeSeconds`, `memoryUsageMb`, `pythonVersion`, `workingDirectory`, `startupValidation`, `performance`, `timestamp`, `runtime`.

## GET `/api/auth/session`
- Purpose: lightweight auth session bootstrap for frontend shell rendering.
- Current behavior: returns a safe dev session if production auth is not configured yet.
- Response: `authenticated`, `user`, `organization`, `cabinet`, `runtime`.

## GET `/api/auth/profile`
- Purpose: user-facing profile identity summary.
- Current behavior: returns the current safe dev user profile and runtime metadata.
- Response: `authenticated`, `user`, `runtime`.

## GET `/api/organization`
- Purpose: active organization profile for workspace context and settings pages.
- Response: `organization`, `runtime`.

## GET `/api/organizations`
- Purpose: list organizations available to the current user in dev/demo multi-tenant mode.
- Response: `organizations`, `activeOrganizationId`, `runtime`.

## GET `/api/organizations/{id}`
- Purpose: return one organization profile by id.
- Response: `organization`, `runtime`.

## POST `/api/organizations/select`
- Purpose: switch the active organization without changing existing auth routes.
- Request: `organizationId`.
- Response: `organizationId`, `cabinetId`, `mode`, `lastChanged`, `organizationCount`, `cabinetCount`, `organization`, `cabinet`, `runtime`.

## GET `/api/wb-cabinet`
- Purpose: current Wildberries cabinet profile for diagnostics and settings UI.
- Response: `cabinet`, `runtime`.

## GET `/api/wb-cabinets`
- Purpose: list cabinets for the active organization in dev/demo multi-cabinet mode.
- Response: `cabinets`, `activeCabinetId`, `organizationId`, `runtime`.

## GET `/api/wb-cabinets/{id}`
- Purpose: return one Wildberries cabinet profile by id.
- Response: `cabinet`, `runtime`.

## POST `/api/wb-cabinets/select`
- Purpose: switch the active Wildberries cabinet without changing existing auth routes.
- Request: `cabinetId`.
- Response: `organizationId`, `cabinetId`, `mode`, `lastChanged`, `organizationCount`, `cabinetCount`, `organization`, `cabinet`, `runtime`.

## GET `/api/workspace/context`
- Purpose: return the current shared organization/cabinet context for the frontend shell.
- Response: `organizationId`, `cabinetId`, `mode`, `lastChanged`, `organizationCount`, `cabinetCount`, `organization`, `cabinet`, `runtime`.

## POST `/api/wb-cabinet/connect`
- Purpose: safe cabinet connect action placeholder for beta UI integration.
- Current behavior: returns a connected dev cabinet profile and does not store tokens.
- Response: `cabinet`, `runtime`.

## POST `/api/wb-cabinet/disconnect`
- Purpose: safe cabinet disconnect action placeholder for beta UI integration.
- Current behavior: returns a disconnected dev cabinet profile and does not store tokens.
- Response: `cabinet`, `runtime`.

## GET `/api/exports`
- Purpose: list export records for the Automation Center.
- Current behavior: returns placeholder dev export records until real exporters are connected.
- Response: `exports`, `runtime`.

## POST `/api/exports`
- Purpose: register a new export request for the Automation Center.
- Current behavior: creates a placeholder export record and a placeholder job record.
- Request: `workspace`, `format`, optional `name`, optional `sku`.
- Response: `export`, `runtime`.

## GET `/api/exports/{id}`
- Purpose: return a single export record by id.
- Response: `export`, `runtime`.

## GET `/api/schedules`
- Purpose: list scheduled report metadata.
- Response: `schedules`, `runtime`.

## POST `/api/schedules`
- Purpose: create a new schedule placeholder contract.
- Request: `name`, `workspace`, `time`, `timezone`, `cadence`, `format`, `enabled`.
- Response: `schedule`, `runtime`.

## PATCH `/api/schedules/{id}`
- Purpose: update an existing schedule placeholder.
- Request: partial update for `enabled`, `time`, `timezone`, `cadence`, `format`, or `status`.
- Response: `schedule`, `runtime`.

## DELETE `/api/schedules/{id}`
- Purpose: remove a schedule from the current placeholder registry.
- Response: `schedule`, `runtime`.

## GET `/api/jobs`
- Purpose: list export and scheduler job metadata.
- Response: `jobs`, `runtime`.

## GET `/api/jobs/{id}`
- Purpose: return a single job record by id.
- Response: `job`, `runtime`.

## GET `/api/notifications`
- Purpose: summary notification hub snapshot with overview, rules, channels, and unread count.
- Current behavior: returns safe dev placeholder data until real delivery infrastructure is connected.
- Response: `status`, `rules`, `channels`, `unreadCount`, `runtime`.

## GET `/api/notifications/rules`
- Purpose: list notification routing rules.
- Response: `rules`, `runtime`.

## POST `/api/notifications/rules`
- Purpose: create a new notification rule placeholder.
- Request: `name`, `enabled`, `channel`, `severity`, `trigger`, `schedule`, `owner`, optional `deepLink`.
- Response: `rule`, `runtime`.

## PATCH `/api/notifications/rules/{id}`
- Purpose: update a notification rule placeholder.
- Request: partial update for rule fields such as `enabled`, `channel`, `severity`, `trigger`, `schedule`, or `deepLink`.
- Response: `rule`, `runtime`.

## DELETE `/api/notifications/rules/{id}`
- Purpose: remove a notification rule from the current placeholder registry.
- Response: `rule`, `runtime`.

## GET `/api/notifications/history`
- Purpose: list delivery history records for the notification hub.
- Response: `history`, `runtime`.

## GET `/api/notifications/channels`
- Purpose: list channel connection and health metadata.
- Response: `channels`, `runtime`.

## POST `/api/notifications/test`
- Purpose: simulate a test notification delivery.
- Current behavior: returns a fake success or failure result depending on the channel and appends placeholder history.
- Request: `channel`, optional `target`, optional `message`.
- Response: `delivery`, `runtime`.

## GET `/api/command-center`
- Purpose: executive command center payload used by the frontend.
- Source: Director, KPI, CFO, Decision, Advisor, Control Center, System Audit.
- Response example shape:
```json
{
  "product": "VOOGLII",
  "screen": "command_center",
  "period": { "label": "current_month", "date_from": "2026-06-01", "date_to": "2026-06-30" },
  "business_health": { "score": 62, "status": "WARNING", "summary": "..." }
}
```

## GET `/api/executive`
- Purpose: official executive payload alias for platform consumption.
- Response: same contract as `/api/command-center`.

## GET `/api/business`
- Purpose: business workspace snapshot.
- Response: `summary`, `trends`, `healthScore`, `healthStatus`, `periods`, `topProducts`, `generatedAt`.

## GET `/api/finance`
- Purpose: finance workspace snapshot.
- Response: `summary`, `quality`, `difference`, `metrics`, `alerts`, `timeline`, `lastUpdated`.

## GET `/api/advertising`
- Purpose: advertising workspace snapshot.
- Response: `summary`, `health`, `metrics`, `recommendations`, `alerts`, `timeline`, `campaigns`, `lastUpdated`.

## GET `/api/products`
- Purpose: products workspace snapshot.
- Response: `summary`, `products`, `recommendations`, `history`, `inventoryPreview`, `alerts`, `timeline`, `actions`, `lastUpdated`.

## GET `/api/inventory`
- Purpose: inventory workspace snapshot.
- Response: `summary`, `health`, `items`, `restockPlan`, `supplyPriority`, `warehouses`, `history`, `alerts`, `timeline`, `metrics`, `lastUpdated`.

## GET `/api/advisor`
- Purpose: advisor workspace snapshot.
- Response: `summary`, `recommendations`, `evidence`, `risks`, `opportunities`, `priorities`, `timeline`, `actions`, `sources`, `conversation`, `insights`, `lastUpdated`.

## POST `/api/advisor/query`
- Purpose: conversational advisor query contract for the AI Copilot MVP.
- Request:
```json
{
  "message": "What should I do today?",
  "context": {
    "workspace": "advisor",
    "sku": "VOO-TS-001",
    "dateFrom": "2026-06-01",
    "dateTo": "2026-06-30",
    "organizationId": "org_vooglii_demo",
    "cabinetId": "cabinet_vooglii_main"
  }
}
```
- Response:
```json
{
  "status": "ok",
  "answer": "Start with finance confidence before using official profit...",
  "summary": "Advisor summary...",
  "recommendations": [],
  "evidence": [],
  "links": [],
  "related": [],
  "confidence": 0.72,
  "runtime": {
    "duration_ms": 88.2,
    "cached": false,
    "stale": false,
    "degraded": false,
    "source": "live"
  }
}
```
- Behavior:
  - frontend sends the user question and optional context only;
  - backend returns a deterministic advisor response based on safe backend snapshots;
  - if deeper advisor query logic is unavailable, the endpoint returns a valid degraded response rather than hanging;
  - degraded responses are still considered valid if the JSON contract is preserved.

## GET `/api/reports`
- Purpose: reports registry snapshot.
- Response: `summary`, `catalog`, `recent`, `templates`, `exports`, `timeline`, `sources`, `lastUpdated`.

## GET `/api/system`
- Purpose: diagnostics and system-facing snapshot.
- Response: `status`, `health`, `quality`, `adsHealth`, `financeHealth`, `cache`, `writeSafety`, `cooldowns`, `lastUpdates`, `coreV2Status`, `controlCenter`, `financeApi`, `lastUpdated`.

## GET `/api/status`
- Purpose: compact service health for infrastructure checks.
- Response: `status`, `wbApi`, `database`, `analytics`, `ads`, `finance`, `system`, `cache`, `slowEndpoints`, `lastSuccessfulSnapshot`, `lastError`, `endpoints`, `version`, `build`, `buildInfo`, `environment`, `timestamp`.

## GET `/api/version`
- Purpose: build metadata for platform/frontend diagnostics.
- Response: `version`, `build`, `git`, `apiVersion`, `environment`, `buildType`, `frontendVersion`.

## Errors
- Shape:
```json
{
  "status": "error",
  "message": "Human-readable error",
  "details": null
}
```

## Usage
- Telegram and FastAPI continue to read from the same analytics builders.
- Frontend consumes these endpoints through the shared `requestJson()` client.
