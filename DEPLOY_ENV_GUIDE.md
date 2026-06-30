# Deploy Env Guide

Before the first production launch, replace these required placeholders in `.env.production`:

- `BOT_TOKEN`
- `WB_TOKEN`
- `WB_STATISTICS_TOKEN`
- `WB_ADVERTISING_TOKEN`
- `POSTGRES_PASSWORD`
- `POSTGRES_URI` if you changed `POSTGRES_PASSWORD`

These variables may stay empty if you do not use them yet:

- `PAYMENT_PROVIDER_TOKEN`

Generate a strong Postgres password on the server:

```bash
openssl rand -base64 24
```

Insert the Telegram bot token into:

```text
BOT_TOKEN=...
```

Insert Wildberries tokens into:

```text
WB_TOKEN=...
WB_STATISTICS_TOKEN=...
WB_ADVERTISING_TOKEN=...
```

Do not commit:

- `.env.production`
- real Telegram tokens
- real Wildberries tokens
- generated local databases

Validate before deploy:

```bash
python scripts/validate_env.py .env.production
```
