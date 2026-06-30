# VOOGLII Platform Release Notes RC1

Version: `0.9.0-rc1`

## Scope

This release candidate focuses on QA hardening, visual consistency, demo readiness, and operational clarity. No new business logic or analytics formulas were introduced.

## Included in RC1

- Demo Mode across the main platform workspaces with explicit runtime/source visibility.
- Product Drilldown, Advisor, Automation Center, Notifications Hub, and Settings flows prepared for first-user demos.
- Release Readiness page with backend mode, version, build, and commit metadata.
- Expanded smoke coverage for backend GET and POST placeholder endpoints.
- Frontend shell cleanup to reduce unnecessary notifications fetching on every page render.

## QA/Polish Highlights

- Improved separation of live, cache, degraded, fallback, and demo runtime states.
- Added shared release documentation and known limitations tracking.
- Standardized release version source via the repo-level `VERSION` file.

## Out of Scope

- Analytics engine formula changes.
- Telegram Agent changes.
- Backend business logic redesign.
- API contract redesign.
