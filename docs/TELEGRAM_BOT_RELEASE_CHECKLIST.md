# TELEGRAM BOT RELEASE CHECKLIST

## Before Release

- Убедиться, что задан `BOT_TOKEN`
- Убедиться, что задан `VOOGLII_TOKEN_ENCRYPTION_KEY`
- Проверить `APP_ENV`
- Проверить `DB_DIR`
- Проверить, что customer help не показывает dev/admin команды
- Проверить, что customer-facing тексты не содержат `Wildberries Agent`, `????`, `UNKNOWN`, `NOT_ACTIVE`, `Legacy fallback`

## Verification Commands

- `python -m pytest`
- `python scripts/release_check.py`
- `python scripts/check_telegram_bot_health.py`
- `python -m py_compile telegram_bot.py vooglii_telegram/ux/*.py`
- `docker compose config`
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`

## Production Readiness

- `/help` показывает только customer-команды
- `/help developer` закрыт для обычного пользователя
- `/system` не показывает инженерные команды обычному пользователю
- `/profile` и `/account` выглядят как клиентские экраны
- `/connect`, `/update`, `/stocks` не содержат mojibake
- PRO-lock текст выглядит как коммерческий upsell, а не ошибка доступа

## Telegram UX 2.0

- Проверить customer-версии экранов `/start`, `/menu`, `/help`, `/home`, `/profile`, `/account`, `/system`, `/business`, `/finance`, `/products`, `/analytics`, `/connect`, `/update`, `/stocks`
- Проверить новый UX-регрессионный набор `tests/test_telegram_customer_ux_v2.py`
- Проверить, что `scripts/release_check.py` падает при возврате запрещённых customer tokens
- Если Docker доступен, дополнительно проверить `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` и `docker compose logs telegram-bot --tail=200`
