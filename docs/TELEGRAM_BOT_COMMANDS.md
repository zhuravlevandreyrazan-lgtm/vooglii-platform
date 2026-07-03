# TELEGRAM BOT COMMANDS

## Customer Commands

- `/start` — запуск VOOGLII Terminal
- `/help` — клиентская помощь
- `/menu` — главное меню
- `/home` — главная сводка
- `/business` — состояние бизнеса
- `/finance` — деньги, прибыль и выплаты
- `/products` — товары, SKU и остатки
- `/analytics` — расширенные отчёты
- `/advisor` — AI-рекомендации
- `/system` — состояние сервиса и данных
- `/profile` — кабинет и подписка
- `/account` — alias на клиентский профиль
- `/connect` — подключение кабинета Wildberries
- `/disconnect` — удаление WB-токена
- `/update` — обновление данных
- `/stocks` — остатки
- `/forecast` — прогноз пополнения
- `/tariff` — тарифы VOOGLII

## Admin Commands

- `/admin`
- `/health`
- `/syncstatus`
- `/apistatus`
- `/control`
- `/migration`
- `/performance`
- `/structure`

## Developer Commands

- `/telegram`
- `/ui`
- `/rc`
- `/data`
- `/adsfullstatsprobe`

## Access Model

- `customer` команды видны в `/help` и `/menu`
- `admin` команды скрыты из customer UX
- `developer` команды скрыты и доступны только developer/admin ролям
- `/help developer` доступен только для developer/admin

## Commercial UX Polish v1.0

- Бренд customer-facing интерфейса унифицирован как `VOOGLII` и `VOOGLII Terminal`
- `/menu`, `/help`, `/home`, `/profile`, `/system`, `/business`, `/finance`, `/products`, `/analytics` приведены к клиентскому формату
- PRO-lock сообщения переписаны в формат value-based upsell

## Telegram UX 2.0

- Добавлен выделенный UX layer в `vooglii_telegram/ux/`
- Реальные customer handlers используют новые renderers для `/start`, `/menu`, `/help`, `/home`, `/profile`, `/account`, `/system`, `/business`, `/finance`, `/products`, `/analytics`, `/connect`, `/update`, `/stocks`
- В customer UX больше не должны появляться `Wildberries Agent`, `/help developer`, `current_month`, `last_30_days`, `Legacy fallback`, `UNKNOWN`, `NOT_ACTIVE`, `/director`, `/cfo`, `/kpi`, `/decision`
- Customer периоды показываются человеческими лейблами: `Сегодня`, `7 дней`, `30 дней`, `Текущий месяц`, `Прошлый месяц`, `Всё время`
