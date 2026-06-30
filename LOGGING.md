# Logging

## Layer

Shared logging is configured in `analytics/logging_config.py`.

## Categories

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

## Safety

The logging filter redacts payloads that look like:

- tokens
- secrets
- authorization headers
- cookies

Sensitive values should not be logged directly by callers.
