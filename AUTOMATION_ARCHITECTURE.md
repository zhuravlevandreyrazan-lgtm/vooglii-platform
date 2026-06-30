# Automation Architecture

## Current Scope
- The Automation Center is a backend-ready control surface for exports, schedules, jobs, and history.
- It does not generate PDF files on the frontend.
- It does not implement Excel generation logic.
- It does not implement cron or a production scheduler yet.

## Export Pipeline
- Frontend opens `/automation` with optional `workspace`, `format`, and `sku` context.
- `POST /api/exports` creates a placeholder export record.
- The backend also creates a placeholder job record to simulate queue registration.
- Future exporters can replace the placeholder stage without changing the frontend contract.

## Scheduler
- `GET /api/schedules` exposes schedule metadata.
- `POST /api/schedules` prepares a new schedule contract.
- `PATCH /api/schedules/{id}` updates enabled state or schedule metadata.
- `DELETE /api/schedules/{id}` marks a schedule as deleted for UI lifecycle simulation.
- Future cron or queue-backed orchestration can plug into the same contract.

## Jobs
- `GET /api/jobs` exposes queue and execution state.
- `GET /api/jobs/{id}` exposes a single job record.
- Job records are lightweight placeholders for running, queued, completed, failed, or cancelled work.

## Future Extensions
- PDF: connect real report rendering behind the existing export contract.
- Excel: connect workbook generation behind the same export creation flow.
- Email: add delivery channels linked to schedules and completed jobs.
- Telegram: add notification routing on top of job completion events.
