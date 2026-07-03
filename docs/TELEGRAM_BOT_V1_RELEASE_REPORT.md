# TELEGRAM BOT V1 RELEASE REPORT

## Что исправлено

- Добавлено шифрование WB-токенов через `security/token_crypto.py`
- Внедрена централизованная permission-модель в `security/permissions.py`
- Добавлен audit trail для privileged actions
- Усилено безопасное логирование и маскирование секретов
- Добавлены `/disconnect`, heartbeat и release healthcheck
- Customer help/menu очищены от developer surface
- Добавлены автономные тесты и `scripts/release_check.py`

## Commercial UX Polish v1.0

- Во всех customer-facing экранах бренд приведён к `VOOGLII` и `VOOGLII Terminal`
- Обновлены customer screens: `/start`, `/menu`, `/home`, `/help`, `/profile`, `/account`, `/system`, `/business`, `/finance`, `/products`, `/analytics`
- Инженерные команды скрыты из customer `/system`
- `/help developer` оставлен только для developer/admin
- PRO-lock переписан как коммерческий upsell

## Telegram UX 2.0

- Добавлен новый customer UX layer в `vooglii_telegram/ux/`
- Заменены реальные customer screens `/start`, `/menu`, `/help`, `/home`, `/profile`, `/account`, `/system`, `/business`, `/finance`, `/products`, `/analytics`, `/connect`, `/update`, `/stocks`
- Убраны запрещённые technical terms из customer surface: `Wildberries Agent`, `/help developer`, `current_month`, `previous_month`, `last_7_days`, `last_30_days`, `Legacy fallback`, `UNKNOWN`, `NOT_ACTIVE`, `Release Candidate`, `UI Spec`, `Product readiness`, `Structure readiness`, `Performance`, `Official Financial Engine`, `local/dev`, `local SQLite`, `PostgreSQL`, `/director`, `/cfo`, `/kpi`, `/decision`, `/control center`, `/rc status`, `/migration readiness`
- Обновлены кнопочные сценарии, чтобы customer callbacks вели в новый UX
- `scripts/release_check.py` теперь включает UX 2.0 проверки и `py_compile` для `vooglii_telegram/ux/*.py`

## Какие UX-тесты добавлены

- `tests/test_telegram_customer_ux.py`
- `tests/test_telegram_customer_ux_v2.py`
- Проверка реальных customer handlers и renderers
- Проверка пустых состояний `/connect`, `/update`, `/stocks`
- Проверка customer `/system`
- Проверка PRO-lock и `/profile` / `/account`

## Как проверить руками

- Открыть в Telegram: `/start`, `/menu`, `/help`, `/home`, `/profile`, `/account`, `/system`, `/business`, `/finance`, `/products`, `/analytics`, `/connect`, `/update`, `/stocks`
- Проверить кнопки: `📅 Сегодня`, `📆 Неделя`, `🗓 Месяц`, `♾ Всё время`, `📊 Отчёт`, `📦 Остатки`, `📢 Реклама`, `⚠ Проблемы`, `🔄 Обновить`, `👑 CEO`, `💰 P&L`, `🤖 AI-советы`, `👤 Кабинет`, `⚙ Меню`

## Что осталось

- `telegram_bot.py` всё ещё остаётся крупным монолитом
- Часть long-tail legacy команд всё ещё содержит старые или технические тексты
- Нужна отдельная волна UX-полировки для редких диагностических и архивных сценариев
