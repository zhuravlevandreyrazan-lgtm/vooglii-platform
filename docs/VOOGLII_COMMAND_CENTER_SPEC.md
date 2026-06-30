# VOOGLII Command Center Screen Specification

Версия: 2.3A  
Статус: Product Design Specification  
Тип: Documentation-only  
Назначение: техническое задание для дизайнера, frontend-разработчика и будущей Web Platform

## 1. Назначение экрана

VOOGLII Command Center — это главный экран платформы.  
Это первая поверхность, которую пользователь открывает утром, чтобы быстро понять состояние бизнеса и определить, что делать дальше.

### Основная задача экрана

За первые 30 секунд экран должен ответить на пять вопросов:

1. Что происходит с бизнесом?
2. Почему это происходит?
3. Что нужно сделать сегодня?
4. Где есть риски?
5. Где есть возможности роста?

### Продуктовая роль

Command Center не является просто dashboard-страницей.  
Это управленческий слой платформы, который:

- объединяет ключевые сигналы из всех Workspace;
- формирует executive view для владельца и операционного руководителя;
- показывает не только цифры, но и причинно-следственный контекст;
- создаёт короткий маршрут: увидеть сигнал → понять причину → перейти к действию.

### Пользователи экрана

- Owner / Founder
- Marketplace Manager
- CFO / Finance Lead
- Analyst
- Administrator / Technical Owner

## 2. Основная структура экрана

Итоговая структура Command Center:

1. Header
2. Business Health
3. Executive Brief
4. KPI Cards
5. Workspace Navigation
6. Today Timeline
7. Today Actions
8. Critical Alerts
9. Recent Events
10. Footer

### Общие правила для всех блоков

Для каждого блока должны быть определены:

- назначение;
- какие данные он показывает;
- откуда берутся данные;
- какие действия доступны пользователю;
- какие состояния возможны;
- как блок ведёт в другой Workspace.

## 3. Header

### Назначение

Дать пользователю контекст: где он находится, за какой период он смотрит данные, насколько актуальна информация и можно ли ей доверять.

### Состав блока

- логотип VOOGLII;
- название платформы;
- подпись: `Business Operating System for Marketplace Sellers`;
- выбор периода;
- статус обновления данных;
- быстрый переход к настройкам;
- глобальный platform status indicator.

### Какие данные показывает

- текущий выбранный период;
- время последнего обновления;
- уровень готовности данных;
- состояние внешних API;
- short account context в будущем.

### Источники данных

- period engine;
- runtime sync status;
- data freshness status;
- system status;
- finance availability status.

### Действия пользователя

- сменить период;
- открыть настройки;
- открыть системный статус;
- обновить контекст в future interactive version.

### Возможные состояния

- данные обновлены;
- данные устарели;
- API cooldown;
- частичная готовность;
- degraded mode;
- warning state;
- normal state.

### UX-правила

- Header не должен быть перегружен.
- Статус готовности должен быть заметен без раскрытия деталей.
- Период должен быть читаемым и единым во всей платформе.

## 4. Business Health

### Назначение

Показать единый индекс состояния бизнеса как главный индикатор дня.

### Что показывает

- общий health score от 0 до 100;
- статус: `GOOD / NORMAL / WARNING / CRITICAL`;
- краткий человеческий вывод;
- уровень доверия к данным;
- optional confidence marker.

### Источники данных

- KPI Engine;
- Director;
- Business Metrics;
- Data Quality;
- Finance status;
- Ads health;
- SKU cost coverage.

### Доступные действия

- открыть Business Workspace;
- перейти в Finance при проблемах прибыли;
- перейти в Products при проблемах покрытия себестоимости или SKU;
- перейти в System при низком доверии к данным.

### Возможные состояния

- confirmed healthy;
- operational only;
- warning due to degraded data;
- critical risk state;
- partially confirmed state.

### Product rules

- Если Finance API недоступен, Business Health не должен выглядеть как полностью подтверждённый.
- Если data quality низкая, score должен сопровождаться текстовым предупреждением.
- Если источники неполные, health остаётся полезным, но визуально помечается как incomplete confidence.

## 5. Executive Brief

### Назначение

Сформировать краткий AI executive summary, который сразу переводит набор сигналов в управленческий смысл.

### Формат brief

Каждый brief должен отвечать на:

1. Что произошло?
2. Почему произошло?
3. Что сделать?
4. Уверенность AI.
5. Источники данных.

### Рекомендуемая структура

Что произошло:  
краткий факт и его важность.

Почему:  
главная причина или наиболее вероятная гипотеза.

Что сделать:

1. первое действие;
2. второе действие;
3. третье действие.

Уверенность:  
High / Medium / Low

Источники:  
какие Workspace, snapshot или data layers использованы.

### Какие данные показывает

- summarized business state;
- главную проблему;
- главную возможность;
- actionable path на сегодня.

### Источники данных

- director-like executive layer;
- Business;
- Finance;
- Products;
- Advertising;
- Analytics;
- trust/status signals.

### Действия пользователя

- перейти по рекомендациям;
- открыть связанный Workspace;
- углубиться в источник сигнала.

### Возможные состояния

- standard executive brief;
- degraded brief with limited confidence;
- no high-confidence recommendations;
- alert-first brief;
- opportunity-first brief.

### UX-правила

- Brief должен быть коротким.
- Brief не должен повторять KPI Cards дословно.
- Brief обязан объяснять рекомендацию.

## 6. KPI Cards

### Назначение

Показать основные цифры платформы в компактном формате для быстрого executive scan.

### Базовый набор карточек

- Продажи
- Прибыль
- К выплате WB
- Реклама
- ROI / ROAS
- Остатки
- Себестоимость
- Business Health

### Контракт каждой карточки

- `title`
- `value`
- `delta`
- `status`
- `comment`
- `source`
- `click action`

### Что показывает блок в целом

- текущие значения;
- изменение к предыдущему периоду;
- статус качества и подтверждённости;
- short interpretation.

### Источники данных

- Business Metrics;
- Financial Engine / Finance layer;
- Advertising layer;
- SKU Registry;
- Stocks / products layer;
- Business Health layer.

### Действия пользователя

- открыть соответствующий Workspace;
- открыть подробности карточки;
- посмотреть причину изменения;
- сверить official vs estimated states.

### Возможные состояния карточек

- normal;
- warning;
- critical;
- unavailable;
- estimated;
- official;
- stale;
- partial.

### Правила дизайна

- value должно быть самым заметным элементом;
- delta должна читаться за долю секунды;
- source и comment остаются вторичным слоем;
- financial cards должны явно разделять official и estimated.

## 7. Workspace Navigation

### Назначение

Дать пользователю карту платформы и быстрый вход в нужную управленческую область.

### Набор Workspace

- Business
- Finance
- Products
- Advertising
- Analytics
- AI
- System

### Каждая карточка Workspace показывает

- название;
- статус;
- 1 главный показатель;
- 1 главный риск;
- переход внутрь Workspace.

### Источники данных

- status summary каждого Workspace;
- главный KPI Workspace;
- главный risk signal Workspace.

### Действия пользователя

- открыть Workspace;
- перейти по риск-сигналу;
- перейти по KPI-сигналу.

### Возможные состояния

- healthy;
- warning;
- critical;
- partial;
- unavailable;
- needs review.

### UX-правила

- Navigation cards не должны быть просто списком ссылок.
- Каждая карточка должна объяснять, зачем туда идти сейчас.
- Workspace с проблемой должен быть виден сразу.

## 8. Today Timeline

### Назначение

Показывать важные события дня в хронологическом виде.

### Какие события входят

- изменение продаж;
- изменение рекламы;
- изменение остатков;
- Finance API restored / cooldown;
- новые риски по SKU;
- новые AI-рекомендации;
- changes in business health;
- sync and data freshness milestones.

### Контракт события

- время;
- тип события;
- краткое описание;
- статус;
- link/action.

### Источники данных

- sync/event layer;
- business alerts;
- finance status changes;
- ad status changes;
- product/stock changes;
- future event journal.

### Действия пользователя

- открыть событие;
- перейти к affected Workspace;
- восстановить контекст изменения.

### Возможные состояния

- informational;
- warning;
- critical;
- resolved;
- requires action.

### UX-правила

- Timeline должен быть коротким и полезным.
- Пользователь должен понимать, что изменилось именно сегодня.
- В timeline не должно быть “шума” ради наполненности.

## 9. Today Actions

### Назначение

Дать пользователю чёткий список конкретных действий на сегодня.

### Примеры действий

- проверить Finance API после cooldown;
- заполнить себестоимость SKU;
- проверить слабую рекламную кампанию;
- заказать поставку;
- проверить выплаты;
- открыть SKU-detail.

### Контракт действия

- `title`
- `reason`
- `priority`
- `confidence`
- `source`
- `action link`

### Источники данных

- AI prioritization layer;
- Critical Alerts;
- Business Health;
- Finance status;
- Products risks;
- Advertising anomalies.

### Действия пользователя

- открыть ссылку действия;
- перейти в Workspace;
- зафиксировать задачу в future state;
- снять неопределённость и принять решение.

### Возможные состояния

- must do today;
- should review;
- opportunity action;
- blocked by data;
- waiting for cooldown or confirmation.

### UX-правила

- действия должны быть конкретными;
- причина действия должна быть видна сразу;
- максимальное число visible actions на первом экране ограничено;
- действия с низкой уверенностью должны быть помечены.

## 10. Critical Alerts

### Назначение

Показать проблемы, которые могут сделать управленческие выводы опасными или требуют немедленного внимания.

### Примеры alerts

- Finance API недоступен;
- себестоимость покрыта меньше 95%;
- реклама тратит бюджет без продаж;
- остатки заканчиваются;
- данные устарели;
- profit model unverified.

### Источники данных

- Finance status;
- System;
- Products / SKU coverage;
- Advertising health;
- Business Metrics;
- Data Quality.

### Действия пользователя

- открыть alert;
- перейти к решению;
- проверить ограничение;
- увидеть next safe action.

### Возможные состояния

- critical;
- warning;
- blocking;
- resolved but still visible in recent cycle.

### Правила

- не больше 3 критических alerts на главном экране;
- остальные уходят в System / Finance / Products;
- красный цвет использовать только для действительно критичных проблем;
- если alert влияет на достоверность, это должно быть сказано прямо.

## 11. Recent Events

### Назначение

Показать последние изменения и обновления без перегрузки основного timeline.

### Примеры событий

- обновлены продажи;
- обновлена реклама;
- изменился статус Finance API;
- появилась новая рекомендация;
- изменился health score.

### Источники данных

- data update log;
- sync status;
- alert lifecycle;
- AI recommendation lifecycle;
- status journal в будущем.

### Действия пользователя

- открыть подробности;
- понять свежесть данных;
- перейти в нужный Workspace.

### Возможные состояния

- recent;
- stale but relevant;
- informational only;
- action-related.

## 12. Footer

### Назначение

Закрепить product identity и дать доступ к низкоприоритетной платформенной информации.

### Базовый текст

VOOGLII  
Business Operating System for Marketplace Sellers

### Содержит

- статус версии;
- время последнего обновления;
- ссылку на System.

### Источники данных

- product metadata;
- version metadata;
- last update timestamp;
- system summary.

### Действия пользователя

- открыть System;
- проверить version/build;
- проверить freshness.

## 13. Layout / Grid

### Desktop

- max width: 1440 px;
- left navigation или top navigation;
- content grid: 12 columns;
- gap: 24 px;
- card radius: 16 px;
- dark theme by default.

### Tablet

- 2-column layout;
- primary blocks remain above detail blocks;
- navigation collapses into compact row or sheet.

### Mobile

- single-column layout;
- сначала Business Health;
- затем Executive Brief;
- затем Today Actions;
- потом KPI;
- навигация должна быть thumb-friendly.

### Layout Priority

На всех поверхностях порядок приоритета один:

1. состояние;
2. короткий вывод;
3. действия;
4. риски;
5. детали;
6. история событий.

## 14. Design Tokens

### Colors

- Primary: `#5B6CFF`
- Secondary: `#7D5CFF`
- Background: `#0B1020`
- Surface: `#121A30`
- Border: `#27324A`
- Text Primary: `#F8FAFC`
- Text Secondary: `#94A3B8`
- Success: `#22C55E`
- Warning: `#F59E0B`
- Danger: `#EF4444`
- Info: `#38BDF8`
- Disabled: `#64748B`

### Typography

- Inter
- табличные цифры для денег и KPI;
- крупные KPI;
- компактные пояснения;
- сильная визуальная иерархия заголовок → значение → пояснение.

### UI Kit

- KPI Card
- Status Card
- AI Insight Card
- Financial Card
- Warning Card
- Success Card
- Critical Card
- Chart Card
- Table Card
- Navigation Card
- Report Header
- Report Footer

## 15. Data States

Пользователь должен всегда понимать статус данных.

### Поддерживаемые состояния

- official
- operational
- estimated
- unavailable
- stale
- cooldown
- partial
- needs_review

### Правила интерпретации

- `official` — подтверждённый контур;
- `operational` — рабочая оценка для управления;
- `estimated` — приближённое значение;
- `unavailable` — данных нет;
- `stale` — данные есть, но устарели;
- `cooldown` — доступ временно ограничен;
- `partial` — часть данных недоступна;
- `needs_review` — вывод нельзя использовать без проверки.

### UX-правила

- official и estimated нельзя визуально смешивать;
- stale и cooldown должны сопровождаться объяснением;
- partial всегда должен уточнять, что именно отсутствует.

## 16. Empty States

### Сценарии empty states

- нет продаж;
- нет рекламы;
- Finance API недоступен;
- себестоимость не заполнена;
- нет остатков;
- нет AI-рекомендаций.

### Правила empty states

- пустое состояние должно объяснять причину;
- пустое состояние должно давать действие;
- пустое состояние не должно выглядеть как ошибка, если это допустимый сценарий;
- пустое состояние должно вести к безопасному следующему шагу.

### Примеры действий

- подключить или обновить данные;
- перейти в Finance / System;
- заполнить себестоимость;
- проверить рекламу;
- перейти к настройке источников.

## 17. Error / Degraded Mode

### Поддерживаемые degraded states

- Finance API cooldown;
- WB API rate limit;
- token problem;
- partial local data;
- old ads data;
- missing SKU cost coverage.

### Для каждого degraded state обязательно

- объяснить причину;
- показать, что можно делать сейчас;
- показать, чего делать нельзя;
- дать следующую безопасную команду или переход.

### Product logic

- degraded mode не должен маскироваться под normal mode;
- ограничения должны быть сформулированы простым бизнес-языком;
- пользователь должен понимать границы доверия к выводам.

## 18. Accessibility

### Правила доступности

- высокая контрастность текста и статусов;
- хорошая читаемость мелких пояснений;
- не полагаться только на цвет;
- текстовые статусы рядом с цветами;
- крупные кликабельные зоны;
- предсказуемая иерархия и spacing;
- money/KPI formatting должно быть легко читаемо.

### Практические требования

- critical state должен быть понятен и без красного цвета;
- delta и status должны сопровождаться подписью;
- mobile touch targets должны быть удобными;
- карточки должны иметь ясные boundaries.

## 19. Future Implementation Notes

Документ должен быть напрямую пригоден для:

- Figma-макета;
- HTML prototype;
- React implementation;
- Telegram adaptation;
- Mobile adaptation.

### Что это означает

- блоки описаны как продуктовые компоненты;
- у блоков есть data contract;
- states и transitions определены заранее;
- layout rules пригодны для responsive implementation;
- screen semantics не завязана только на Telegram.

Код в рамках этого sprint не реализуется.

## 20. Expected Result

После выполнения должен существовать документ:

`docs/VOOGLII_COMMAND_CENTER_SPEC.md`

Этот документ должен стать основой для следующего sprint:

`2.3B — High-Fidelity Visual Prototype`

### Финальный критерий качества

Документ должен позволить:

- дизайнеру построить Figma-экран без домысливания продуктовой логики;
- frontend-разработчику понять структуру layout и состояний;
- product manager-у проверить соответствие экрану бизнес-цели;
- future web/mobile team использовать единый контракт Command Center.

Python-код, runtime и текущая бизнес-логика при этом не меняются.
