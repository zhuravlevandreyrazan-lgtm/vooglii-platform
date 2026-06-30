# Known Limitations

## Release Candidate 1

- Demo Mode is frontend-driven and designed for showcase scenarios; backend mutable state remains placeholder-oriented.
- Automation exports, schedules, and jobs keep contract-compatible placeholder behavior and do not produce production artifacts.
- Notifications delivery is simulated in dev/RC environments for Telegram, email, and webhook flows.
- Some live workspaces can fall back to cached or degraded snapshots when source data is unavailable.
- Smoke run results are not persisted in-product yet and should be tracked manually during QA sessions.
