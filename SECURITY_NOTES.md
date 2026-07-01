# Security Notes

## Current Scope
- The current auth layer is beta-safe and uses dev or demo placeholder profiles.
- Real Wildberries tokens are not stored in the frontend.
- The backend does not persist real Wildberries tokens in this implementation.

## Wildberries Token Handling
- Never place real WB tokens in frontend code, browser storage, or demo fixtures.
- Any future `connect` flow must send tokens only over HTTPS in production.
- Any future token storage must remain backend-side only.
- Dev and demo flows use safe placeholders instead of real secrets.

## Notification Secrets
- Telegram bot tokens must never be stored in the frontend.
- Email SMTP credentials must remain backend-side only.
- Webhook secrets must remain backend-side only.
- Production notification delivery must happen only through backend infrastructure.
- Frontend only manages notification settings, placeholders, and safe test flows.

## Future Auth Direction
- Production auth should move to JWT or secure server sessions.
- Role-aware access control should be enforced server-side.
- Cookie or session handling should be added only with CSRF and transport security in place.

## RBAC Notes
- Frontend permission-based hiding is a UX layer only; backend permission checks are authoritative.
- Role changes, disable actions, and denied access attempts are recorded through backend audit hooks.
- The current actor scaffold is intentionally temporary and should be replaced by real session identity in the production auth rollout.
