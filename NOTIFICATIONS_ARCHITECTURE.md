# Notifications Architecture

## Current Scope
- Notifications Hub is a backend-ready control surface for channels, rules, history, and safe test delivery.
- Real Telegram, email, and webhook delivery are not enabled in this phase.
- In-app notifications are represented as placeholder delivery metadata and UI history.

## Channels
- `telegram`
- `email`
- `webhook`
- `in_app`

Each channel exposes status, connection metadata, last test time, delivery health, and a placeholder setup action.

## Rules
- Rules define which events should be routed to which channel.
- Rules carry severity, trigger conditions, schedules, owner metadata, and optional deep links.
- Future backend event engines can attach to the current rule contract without changing the frontend shape.

## Events And Delivery Pipeline
- A backend event triggers rule evaluation.
- Matching rules create delivery attempts.
- Delivery attempts produce history records and status metadata.
- In the current phase, `POST /api/notifications/test` returns a simulated delivery result instead of a real send.

## History
- History stores title, channel, status, time, target, workspace context, error, and deep link.
- History is used to prepare future auditability for notification delivery.

## Future Extensions
- Telegram delivery: connect backend bot infrastructure and queue processing.
- Email delivery: connect backend SMTP or transactional provider delivery.
- Webhook delivery: connect signed backend webhooks with retry policy.
- Scheduled report delivery: use Automation Center schedules as upstream event sources for Notifications Hub.
