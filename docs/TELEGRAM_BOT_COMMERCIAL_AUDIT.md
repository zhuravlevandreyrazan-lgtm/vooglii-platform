# TELEGRAM BOT COMMERCIAL AUDIT

Дата аудита: 2026-07-03  
Проект: VOOGLII Terminal / Wildberries AI Agent  
Объект аудита: Telegram-бот `telegram_bot.py` и связанная production-инфраструктура

## 1. Краткое резюме

Telegram-бот VOOGLII находится в рабочем состоянии и уже интегрирован в production-контур как отдельный Docker-сервис, но до коммерческого релиза он пока не доведен. Бот умеет подключать кабинет, синхронизировать данные, строить отчеты и использовать общую SQLite-базу с backend, однако текущая реализация остается монолитной, технически перегруженной и недостаточно защищенной для клиентского SaaS-использования.

Оценка коммерческой готовности: **61%**

- Общий статус: `WARNING`
- Главный технический риск: монолитный `telegram_bot.py` на 19k+ строк с большим количеством sync I/O внутри async-обработчиков и сильной связностью с backend/analytics.
- Главный UX-риск: пользовательская поверхность смешана с dev/admin-командами, а часть сообщений до сих пор выглядит как internal tooling, а не как коммерческий продукт.
- Главный security-риск: WB-токены пользователей сохраняются в SQLite в открытом виде, а диагностические команды частично логируют чувствительные данные.

## 2. Таблица аудита

| Блок | Статус | Что найдено | Риск | Рекомендация | Приоритет |
|---|---|---|---|---|---|
| Архитектура бота | WARNING | `telegram_bot.py` содержит 19475 строк и совмещает handlers, тексты, SQLite, API-клиенты, диагностику, меню и бизнес-логику | Сложно безопасно развивать, тестировать и локализовать; высокий шанс регрессий | Разделить на модули: handlers, services, repositories, renderers, admin/dev tools, command registry | P1 |
| Границы ответственности | WARNING | `analytics/business.py`, `analytics/finance.py`, `analytics/wb_cabinet_manager.py` импортируют `telegram_bot` напрямую | Backend зависит от внутренностей Telegram-бота; трудно масштабировать и переиспользовать | Вынести snapshot/builders в отдельный shared service layer без импорта bot entrypoint | P1 |
| Командная поверхность | CRITICAL | Зарегистрировано 82 slash-команды в `telegram_bot.py:21032`; клиентские, dev и admin сценарии смешаны | Пользователь видит избыточную и опасную поверхность; выше риск ошибочного доступа и плохого UX | Разделить команды на commercial, admin и dev; скрыть технические команды из общего меню и help | P0 |
| Доступы и роли | CRITICAL | Доступ основан в основном на `tariff` и `ADMIN_IDS`; роль в `user_manager.py` почти не участвует в авторизации | Нет полноценных клиентских ролей и надежной модели доступа для коммерческого продукта | Внедрить RBAC для Telegram-бота: owner/admin/manager/viewer или согласованную с платформой модель | P0 |
| Хранение секретов | CRITICAL | `wb_token` хранится в `users` как обычный `TEXT` в SQLite (`db_manager.py:34`, `user_manager.py:57-58`) | Компрометация БД = компрометация кабинетов WB клиентов | Перейти на шифрование токенов at-rest и минимизацию доступа к колонке | P0 |
| Логирование секретов | CRITICAL | `_log_ads_token_debug` в `telegram_bot.py:4172` и `load_sales.py:754` логирует prefix/suffix токена; в `load_sales.py` много raw `print()` HTTP-диагностики | Утечка чувствительных данных через docker logs и stdout | Удалить token preview, унифицировать secure logging, запретить печать заголовков/ответов с секретами | P0 |
| Error handling | WARNING | Глобальный `error_handler` в `telegram_bot.py:21003` делает только `print("ERROR:", context.error)` | Потеря контекста инцидентов, слабая диагностика production-ошибок | Перейти на structured logging с user_id, command, traceback, correlation id | P1 |
| Startup/Shutdown | WARNING | Бот запускается через `run_polling()` без явных lifecycle hooks | Меньше контроля над startup readiness и корректным shutdown фоновых задач | Добавить явные startup/shutdown hooks и release-safe boot checks | P2 |
| Healthcheck | WARNING | `scripts/check_telegram_bot_health.py` проверяет токен, init_db, файл БД и `SELECT 1`, но не проверяет polling loop и Telegram API | Возможны ложные “healthy”, если polling упал после старта | Дополнить health-модель heartbeat-файлом/меткой последнего poll tick и bot identity probe | P1 |
| Docker production | OK | Есть отдельный сервис `telegram-bot`, `restart: unless-stopped`, общий volume `/app/storage`, отдельный healthcheck | Базовая production-инфраструктура уже настроена | Сохранить текущую схему, усилить только readiness/logging/access controls | P2 |
| Совместимость с backend | WARNING | Бот и backend делят одну SQLite через общий volume | Простая интеграция, но есть риск lock contention и blast radius | Включить WAL/busy_timeout, сократить длительность транзакций, вынести тяжелые sync-процессы | P1 |
| SQLite подключение | WARNING | `db_manager.get_conn()` включает только `PRAGMA foreign_keys = ON`; нет WAL, `busy_timeout`, retry policy | Риск `database is locked` при одновременной активности backend и bot | Включить SQLite tuning для multi-process режима и описать политику повторов | P1 |
| Async/performance | WARNING | Во многих async-обработчиках используются синхронные `sqlite3.connect(...)` и `httpx.get/post/request(...)` | Возможны зависания event loop и деградация UX на тяжелых командах | Вынести тяжелые операции в worker/service layer или thread executor; ограничить sync I/O в handlers | P1 |
| Background jobs | WARNING | `background_jobs.py` использует sync SQLite и sync loader’ы, пишет в общую БД | Конкуренция за БД и непредсказуемое поведение при ошибках внешних API | Усилить lock strategy, retry policy и observability фоновых задач | P1 |
| Пустая БД / нет данных | WARNING | Есть много fallback-веток и проверок, но поведение неоднородно по командам и сообщениям | Пользователь может видеть нули, технические статусы или разный no-data UX | Централизовать no-data policy для Telegram-ответов и customer-facing формулировок | P1 |
| UX и бренд | WARNING | `/start` все еще начинается с `Wildberries Agent`; часть текстов остается технической или англоязычной | Продукт выглядит как internal MVP, а не как коммерческий VOOGLII-сервис | Провести полную бренд- и UX-полировку текстов, help, onboarding, account screens | P1 |
| Help/Menu | WARNING | `/help developer` доступен через основное меню, меню смешивает коммерческий и тех. слой | Новый клиент получает лишнюю сложность и может попасть в dev-сценарии | Разделить main menu и internal help, вывести developer/admin help из customer UX | P0 |
| Формат сообщений | WARNING | `send_long()` просто режет текст по чанкам; нет общей системы форматирования и шаблонов | Отчеты читаются нестабильно, длинные ответы могут выглядеть тяжело | Ввести единые renderers для executive/report/alert/empty state сообщений | P2 |
| Тексты и кодировка | WARNING | В коде есть англоязычные и частично поврежденные строки (mojibake) | Падает доверие к продукту, растет риск непонимания пользователем | Провести отдельный текстовый cleanup по Telegram-боту и проверить кодировку файлов | P1 |
| Доступ к тех. командам | CRITICAL | Защита части технических команд держится только на `admin(update)` с `ADMIN_IDS` | Недостаточно гибко и плохо масштабируется на несколько клиентов/операторов | Ввести явное разделение privileged commands и централизованные permission checks | P0 |
| `.env` шаблоны | WARNING | В `.env.example` и `.env.production.example` `BOT_TOKEN` заполнен placeholder-значением, а не пустым значением | Возможен неочевидный старт с ложной конфигурацией | Делать строгую валидацию формата токена и пустые безопасные шаблоны | P2 |
| Логирование production | WARNING | Бот использует `_configure_telegram_logging()`, а не `analytics.logging_config.configure_logging()` с `SensitiveDataFilter` | Защита логов неполная и несогласованная по проекту | Унифицировать logging pipeline проекта и применить sensitive data filter к боту | P1 |
| Тестовое покрытие | OK | Есть `tests/scenario_suite.py`, `tests/smoke_readonly.py`, `tests/telegram_security.py`, `tests/telegram_identity.py`, `tests/readonly_runtime_guard.py` | Это хорошая база, но пока не покрывает polling/real command runtime глубоко | Сохранить readonly-тесты и добавить integration tests по ключевым командам и access policy | P2 |
| Готовность к multi-client | CRITICAL | Логика аккаунтов, ролей, токенов и тарифов еще не оформлена как полноценная multi-tenant модель | Трудно безопасно продавать нескольким клиентам и командам одного кабинета | Спроектировать tenant/account/workspace/access model до масштабирования продаж | P0 |

## 3. Что уже реализовано

### 3.1. Production-инфраструктура

- Отдельный Docker-сервис `telegram-bot` в [docker-compose.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.yml:32).
- Production override через [docker-compose.prod.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.prod.yml:28).
- Общий volume `storage_data:/app/storage` для backend и bot.
- `restart: unless-stopped` для bot-сервиса.
- Отдельный healthcheck через [scripts/check_telegram_bot_health.py](/C:/Users/Andrey/Desktop/WildberriesAgent/scripts/check_telegram_bot_health.py:1).
- Чтение токена из `.env.production`.

### 3.2. Команды и сценарии

Фактически в боте зарегистрирована большая командная поверхность в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:21032), включая:

- базовые входные точки: `/start`, `/menu`, `/help`, `/home`, `/profile`
- подключение кабинета и синхронизацию: `/connect`, `/update`, `/syncstatus`
- executive/business reports: `/dashboard`, `/report`, `/business`, `/advisor`, `/ceo`, `/system`
- финансы и продажи: `/finance`, `/profit`, `/cashflow`, `/expense`, `/sales`, `/orders`
- товарная аналитика: `/products`, `/product`, `/sku`, `/topprofit`, `/losers`, `/categories`, `/abc`
- реклама: `/ads`, `/adsupdate`, `/adsaudit`, `/advert`, `/analytics`
- остатки и прогноз: `/stocks`, `/stock`, `/forecast`, `/replenishment`
- тарифы и биллинг-сценарии: `/tariff`, `/buy`, `/payment`
- админ/технические сценарии: `/admin`, `/telegram`, `/ui`, `/performance`, `/migration`, `/control`, `/structure`, `/health` и другие

### 3.3. Интеграции и полезные решения

- Бот использует ту же SQLite-базу, что и backend.
- Реализованы фоновые синхронизации и первичный init sync через `job_queue`.
- Есть готовые snapshot/builders, которые уже питают и web-платформу, и Telegram-слой.
- Есть сценарии health/status/audit, полезные для внутренних операций и поддержки.
- Есть базовые тесты на readonly-поведение и security/runtime guard.

## 4. Что реально работает, что дублируется, что не подходит для клиента

### 4.1. Команды, которые выглядят как ядро коммерческой версии

- `/start`
- `/menu`
- `/connect`
- `/update`
- `/dashboard`
- `/report`
- `/business`
- `/finance`
- `/advert`
- `/products`
- `/stocks`
- `/forecast`
- `/advisor`
- `/system`
- `/profile`
- `/tariff`

### 4.2. Дублирующиеся или пересекающиеся сценарии

- `/help` и `/menu` ведут в одну точку.
- `/buy` и `/pro` дублируют один сценарий.
- `/today`, `/week`, `/month`, `/pnl` завязаны на похожие report-сценарии.
- `/product` и `/products`, `/stock` и `/stocks`, `/finance` и `/financial` создают лишнюю сложность в UX.
- `/ceo`, `/morning`, `/director`, `/decision`, `/command`, `/cfo`, `/kpi` частично пересекаются по смыслу executive-аналитики.

### 4.3. Команды, которые нужно скрыть из коммерческой версии или перевести в admin/dev mode

- `/adsfullstatsprobe`
- `/apistatus`
- `/syncstatus`
- `/migration`
- `/control`
- `/structure`
- `/rc`
- `/performance`
- `/data`
- `/telegram`
- `/ui`
- `/admin`
- диагностические подкоманды `sales`, `finance`, `ads`, `system`, `dashboard`, если они используются как internal tooling

### 4.4. Честная оценка по user scenarios

- `/start`, `/dashboard`, `/report`, `/advisor` и `/system audit` как класс сценариев в проекте присутствуют.
- `/profit audit` поддерживается через команду `/profit` с audit-сценарием.
- `/sku analytics` и `/advertising analytics` как прямые slash-команды не оформлены отдельно; сейчас это распределено между `/sku`, `/advert`, `/analytics` и смежными командами.

## 5. Архитектурные замечания

### 5.1. Структура `telegram_bot.py`

Ключевые точки:

- `admin()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:274)
- `access()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:4231)
- `send_long()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:4065)
- `start_command()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:7010)
- `connect_command()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:7316)
- `menu_command()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:20580)
- `error_handler()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:21003)
- `main()` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:21007)

Проблема не в том, что файл “большой сам по себе”, а в том, что он одновременно является:

- entrypoint приложения;
- command registry;
- user interface layer;
- DB access layer;
- WB API client layer;
- diagnostic toolbox;
- частью shared analytics-платформы.

Такой дизайн еще допустим на этапе MVP, но перед коммерческим релизом он становится главным источником технического риска.

### 5.2. Связь с backend и analytics

Backend-модули напрямую импортируют Telegram-слой:

- [analytics/business.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/business.py:7)
- [analytics/finance.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/finance.py:5)
- [analytics/wb_cabinet_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/wb_cabinet_manager.py:27)

Это уже работает, но архитектурно означает, что Telegram-бот стал фактическим shared-domain модулем, хотя он должен быть только delivery layer. Для версии 1.0 это стоит зафиксировать как P1-рефакторинг.

## 6. UX и коммерческий вид

### 6.1. Что уже хорошо

- В части меню и executive-описаний уже заметна попытка привести продукт к стилю VOOGLII.
- Есть единый shell команд и onboarding через `/start` и `/menu`.
- Бот умеет отдавать насыщенные по смыслу аналитические ответы, а не только технические статусы.

### 6.2. Что сейчас мешает коммерческому восприятию

- `/start` начинается с `Wildberries Agent`, а не с единого бренда VOOGLII.
- В customer-facing поверхности присутствует `/help developer`.
- Экран account содержит явно технические строки: `ACCOUNT`, `plan: local/dev`, `data retention: local SQLite` в [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:18346).
- В тексте команд и подсказок есть английские хвосты и местами поврежденная кодировка.
- `/connect` требует вставлять токен в виде сырой команды, что неудобно и тревожно для клиента.
- Нет аккуратного разделения между “нет данных”, “идет синхронизация”, “ошибка WB API”, “недостаточно прав”.

## 7. Надежность

### 7.1. Позитивные стороны

- Бот уже запускается отдельным сервисом и не зависит от frontend.
- Есть фоновые джобы и initial sync.
- Healthcheck хотя бы проверяет базовую доступность БД.

### 7.2. Основные риски

- Синхронные внешние HTTP-вызовы и SQLite-операции внутри async handlers.
- Слабый глобальный error handler.
- Недостаточный healthcheck для long-running polling-процесса.
- Возможная конкуренция за SQLite между bot/backend/background jobs.
- Неоднородное поведение команд при пустой БД и отсутствии данных WB.

## 8. Безопасность

### 8.1. Критические находки

1. Хранение WB-токена в открытом виде:
   - [db_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/db_manager.py:34)
   - [user_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/user_manager.py:57)
   - [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:7316)

2. Диагностическое логирование токена и HTTP-трасс:
   - [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:4172)
   - [load_sales.py](/C:/Users/Andrey/Desktop/WildberriesAgent/load_sales.py:754)

3. Недостаточно строгая модель доступа:
   - `admin()` завязан на `ADMIN_IDS`
   - `access()` завязан на tariff/features
   - роль пользователя не является полноценным security boundary

### 8.2. Что стоит проверить перед продажами

- кто и как сможет управлять ботом для разных клиентов;
- как будут выдаваться доступы команде клиента;
- как будет проходить отзыв доступа;
- как будут ротироваться и удаляться WB-токены;
- какие команды доступны support/admin/operator ролям;
- как исключить чувствительные данные из логов и экспортов.

## 9. Production/Docker

### 9.1. Что сделано корректно

- Отдельный сервис `telegram-bot` определен в [docker-compose.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.yml:32).
- Запуск идет через `python -u telegram_bot.py` в [docker-compose.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.yml:36).
- Production env задается через [docker-compose.prod.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.prod.yml:28).
- Используется общий volume `/app/storage`.
- Healthcheck подключен.

### 9.2. Что остается слабым местом

- Healthcheck не проверяет рабочий polling state.
- Нет отдельной production-политики логирования.
- Нет формализованной защиты от DB lock contention.
- Нет release-safe config validation для токенов и privileged settings.

## 10. Работа с базой данных

### 10.1. Текущее состояние

- Путь к SQLite управляется через `DB_DIR`; bot и backend используют общую БД.
- Таблицы создаются через `init_db()`.
- Есть таблицы пользователей, sales, notifications, sync_locks и др.

### 10.2. Риски

- Много прямых `sqlite3.connect(DB_NAME)` по коду.
- Нет явного WAL/busy timeout в [db_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/db_manager.py:12).
- Есть вероятность lock’ов при параллельных sync/job/backend запросах.
- Хранение секретов в той же БД увеличивает последствия компрометации.

## 11. Производительность

### 11.1. Что создает риск деградации

- Sync `httpx` внутри async handlers.
- Sync `sqlite3` внутри async handlers.
- Тяжелые аналитические команды могут выполнять большие вычисления в ответ на пользовательский запрос.
- Повторные расчеты и запросы не всегда явно кэшируются на уровне Telegram delivery layer.

### 11.2. Что потребуется до 1.0

- инвентаризация самых тяжелых команд по latency;
- перенос тяжелых операций в сервис/worker слой;
- таймауты и user-friendly progress states;
- профилирование команд `/dashboard`, `/report`, `/finance`, `/advert`, `/system`.

## 12. Логирование и диагностика

### 12.1. Уже есть

- startup prints и простая базовая диагностика;
- healthcheck script;
- internal diagnostic commands.

### 12.2. Недостатки

- Слишком много `print()` вместо structured logger.
- Логи местами могут содержать чувствительные данные.
- Нет единого формата `user_id / command / duration / result / error`.
- Нет четкого деления на audit logs и debug logs.

## 13. Готовность к коммерческому релизу

### 13.1. Что уже можно считать готовым

- базовый production deployment через Docker;
- общий storage с backend;
- бот как отдельный сервис;
- набор бизнес-команд и аналитических ответов;
- начальная основа для health и readonly тестов.

### 13.2. Что выглядит как MVP

- монолитная архитектура;
- смешение customer/dev/admin UX;
- сырой onboarding через `/connect <token>`;
- тарифно-ориентированная, а не ролевая модель доступа;
- частично технические тексты;
- простая схема логирования и healthchecks.

### 13.3. Что обязательно исправить до продаж

- убрать хранение WB-токенов в открытом виде;
- убрать утечки чувствительных данных в логи;
- спрятать dev/admin команды из клиентской поверхности;
- внедрить полноценную access model;
- унифицировать customer-facing тексты и no-data/error states;
- усилить SQLite concurrency strategy.

## 14. Список проблем по приоритетам

### P0 — обязательно исправить до коммерческого запуска

- Хранение `wb_token` в открытом виде в SQLite.
- Логирование частей токенов и raw HTTP diagnostics.
- Отсутствие полноценного RBAC/permission model для Telegram-бота.
- Смешение customer menu с developer/admin help.
- Слишком широкая и техническая командная поверхность для клиента.
- Отсутствие multi-client access design для безопасной продажи нескольким клиентам.

### P1 — исправить перед активными продажами

- Декомпозиция `telegram_bot.py`.
- Разрыв прямой зависимости backend analytics от `telegram_bot`.
- Structured logging и нормальный global error handling.
- SQLite tuning: WAL, busy_timeout, retry policy.
- Снижение sync I/O внутри async handlers.
- Полная бренд- и текстовая полировка Telegram UX.
- Единая policy для empty states, errors, sync in progress, no data.
- Усиление healthcheck и runtime observability.

### P2 — улучшить после релиза

- Улучшенный onboarding flow с кнопками и пошаговым сценарием.
- Более сильное форматирование длинных отчетов.
- Улучшенный account/billing UX.
- Расширенные product analytics и client education flows.
- Более глубокое integration test покрытие по polling/runtime.

## 15. Roadmap Telegram Bot v1.0

### Этап 1: стабилизация

- Убрать утечки секретов из логов.
- Ввести secure storage policy для WB-токенов.
- Усилить global error handling и structured logs.
- Добавить runtime heartbeat для healthcheck.
- Настроить SQLite WAL/busy_timeout/retry policy.

### Этап 2: коммерческий UX

- Очистить `/start`, `/menu`, `/help`, `/profile`, `/account` от технических хвостов.
- Сформировать короткий коммерческий command set.
- Убрать developer/admin сценарии из клиентского меню.
- Переписать onboarding подключения кабинета в понятном customer tone.
- Привести все empty/no-data/error messages к единому стилю VOOGLII.

### Этап 3: безопасность и доступы

- Внедрить RBAC/permissions для Telegram-бота.
- Разделить owner/admin/operator/viewer сценарии.
- Ограничить технические команды.
- Ввести audit trail по privileged commands и token actions.

### Этап 4: подготовка к нескольким клиентам

- Спроектировать tenant/account/workspace модель.
- Разделить доступы внутри одной клиентской команды.
- Продумать safe onboarding/offboarding пользователей.
- Подготовить основу под подписочную модель, биллинг и customer success operations.

### Этап 5: финальная полировка

- Разделить монолит на модули.
- Вынести shared analytics из `telegram_bot.py` в service layer.
- Добавить performance profiling ключевых команд.
- Расширить integration tests и release checklist.

## 16. Точные ссылки на ключевые находки

- `admin()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:274)
- `send_long()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:4065)
- `_log_ads_token_debug()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:4172)
- `access()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:4231)
- `start_command()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:7010)
- `connect_command()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:7316)
- `_account_text()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:18346)
- `menu_command()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:20580)
- `error_handler()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:21003)
- `main()` — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:21007)
- command registry — [telegram_bot.py](/C:/Users/Andrey/Desktop/WildberriesAgent/telegram_bot.py:21032)
- logging filter, который не используется ботом — [analytics/logging_config.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/logging_config.py:16)
- SQLite connection setup — [db_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/db_manager.py:12)
- users table with `wb_token` — [db_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/db_manager.py:32)
- `save_user()` — [user_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/user_manager.py:57)
- `user_has_access()` — [user_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/user_manager.py:81)
- `set_role()` — [user_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/user_manager.py:105)
- healthcheck script — [scripts/check_telegram_bot_health.py](/C:/Users/Andrey/Desktop/WildberriesAgent/scripts/check_telegram_bot_health.py:1)
- bot service — [docker-compose.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.yml:32)
- production bot override — [docker-compose.prod.yml](/C:/Users/Andrey/Desktop/WildberriesAgent/docker-compose.prod.yml:28)
- verbose debug logging in loaders — [load_sales.py](/C:/Users/Andrey/Desktop/WildberriesAgent/load_sales.py:754)
- backend imports telegram layer — [analytics/business.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/business.py:7), [analytics/finance.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/finance.py:5), [analytics/wb_cabinet_manager.py](/C:/Users/Andrey/Desktop/WildberriesAgent/analytics/wb_cabinet_manager.py:27)

## 17. Итог

Telegram-бот уже можно считать сильным operational MVP и хорошей базой для релизной версии, но не финальным коммерческим продуктом. Главная задача перед версией 1.0 — не добавлять новые команды, а сузить поверхность, усилить security, стабилизировать runtime-поведение и довести пользовательский слой до единого бренда VOOGLII.

На текущем этапе бот готов для controlled use и внутренней эксплуатации, но для масштабируемых коммерческих продаж требуется обязательный цикл hardening по P0 и P1 пунктам из этого отчета.
