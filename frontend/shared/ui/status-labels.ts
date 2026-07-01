import type { ApiRuntimeSource, WorkspaceDiagnostics } from "@/shared/api/api-types";

const STATUS_LABELS: Record<string, string> = {
  GOOD: "Норма",
  READY: "Норма",
  OK: "Норма",
  HEALTHY: "Норма",
  NORMAL: "Норма",
  AVAILABLE: "Норма",
  ACTIVE: "Активно",
  OPERATIONAL: "Работает",
  WARNING: "Требует внимания",
  PARTIAL: "Требует внимания",
  WATCH: "Наблюдать",
  DEGRADED: "Данные частично недоступны",
  CRITICAL: "Критично",
  ERROR: "Критично",
  BLOCKED: "Критично",
  UNKNOWN: "Нет данных",
  UNAVAILABLE: "Нет данных",
  INSUFFICIENT_DATA: "Нет данных",
  PENDING: "Ожидаем данные",
  OPEN: "Открыто",
  REVIEW: "Нужно проверить",
  PLANNED: "Запланировано",
  GENERATED: "Сформировано",
  HIGH: "Высокий уровень",
  MEDIUM: "Средний уровень",
  LOW: "Низкий уровень",
  SENT: "Отправлено",
  FAILED: "Ошибка",
  RUNNING: "В процессе",
  QUEUED: "В очереди",
  COMPLETED: "Готово",
  PAUSED: "На паузе",
  MUTED: "Отключено"
};

const WORKSPACE_LABELS: Record<string, string> = {
  executive: "Главная",
  business: "Бизнес",
  finance: "Финансы",
  advertising: "Реклама",
  products: "Товары",
  inventory: "Остатки",
  automation: "Автоматизация",
  notifications: "Уведомления",
  reports: "Отчеты",
  advisor: "ИИ-советник",
  team: "Команда",
  settings: "Настройки",
  platform: "Платформа",
  system: "Система"
};

const PERIOD_LABELS: Record<string, string> = {
  yesterday: "Вчера",
  today: "Сегодня",
  tomorrow: "Завтра",
  latest: "Последнее обновление",
  sync: "Синхронизация",
  audit: "Аудит",
  analytics: "Аналитика",
  health: "Состояние",
  import: "Импорт",
  forecast: "Прогноз",
  restock: "Пополнение",
  sevenDays: "7 дней",
  thirtyDays: "30 дней",
  ninetyDays: "90 дней",
  week: "На неделе"
};

const KNOWN_TEXT_LABELS: Record<string, string> = {
  "LIVE BACKEND": "Данные обновлены",
  "LIVE CACHE": "Данные недавно обновлены",
  DEGRADED: "Данные частично недоступны",
  "No business data available": "Нет данных за выбранный период",
  "Finance requires attention": "Требуется внимание к финансам",
  "Management attention is required": "Требуется управленческое внимание",
  "Inventory pressure detected": "Требуется внимание к остаткам",
  "Review inventory pressure before scaling demand": "Проверьте остатки перед масштабированием продаж",
  Healthy: "Норма",
  Watch: "Наблюдать",
  Ready: "Готово",
  Today: "Сегодня",
  Tomorrow: "Завтра",
  Week: "На неделе",
  "Executive Brief": "Краткий вывод",
  Difference: "Расхождение",
  "Backend is unreachable.": "Не удалось загрузить данные. Попробуйте обновить страницу позже.",
  "Unable to load data": "Не удалось загрузить данные",
  "Empty state": "Нет данных",
  "Data for this block is not available yet.": "Данные для этого блока пока недоступны.",
  "Command Center": "Центр управления",
  Source: "Источник",
  Updated: "Обновлено",
  "Refresh snapshot": "Обновить данные",
  "Coming soon": "Раздел в подготовке",
  Revenue: "Выручка",
  Profit: "Прибыль",
  "Operating Profit": "Операционная прибыль",
  Margin: "Маржинальность",
  Orders: "Заказы",
  "Advertising Spend": "Расходы на рекламу",
  "Linked Spend": "Связанные расходы",
  "Unlinked Spend": "Нераспределенные расходы",
  Trust: "Надежность",
  Status: "Статус",
  "Ads Health": "Состояние рекламы",
  "Inventory Health": "Состояние остатков",
  "Forecast Coverage": "Покрытие прогноза",
  "Days Left Average": "Средний запас в днях",
  "Warehouse Count": "Складов в отчете",
  "Products Summary": "Сводка по товарам",
  "Routing rules": "Правила маршрутизации",
  Rules: "Правила",
  Enabled: "Включено",
  Muted: "Отключено",
  Trigger: "Условие",
  Owner: "Ответственный",
  "Last triggered": "Последний запуск",
  "Not triggered yet": "Пока не запускалось",
  "Mute Rule": "Отключить правило",
  "Enable Rule": "Включить правило",
  "Open workspace": "Открыть раздел",
  "Recent automation events": "Последние события",
  "Automation Timeline": "Лента автоматизации",
  "Scheduled reports": "Автоматические выгрузки",
  Schedules: "Расписания",
  "Last run": "Последний запуск",
  "Next run": "Следующий запуск",
  "Pause schedule": "Остановить расписание",
  "Enable schedule": "Запустить расписание",
  "Not run yet": "Еще не запускалось",
  "AI Insight": "Инсайт ИИ",
  "Backend-ready analysis": "Аналитический вывод",
  "Top risk": "Главный риск",
  "Top opportunity": "Точка роста",
  Recommendation: "Рекомендация",
  Recommendations: "Рекомендации",
  "Action plan": "План действий",
  "No warehouse status available.": "Статус складов появится после синхронизации.",
  "No completed exports yet": "Завершенных выгрузок пока нет",
  Unknown: "Нет данных",
  Pending: "Ожидаем данные",
  Strong: "Норма",
  Stable: "Стабильно",
  Scaling: "Есть потенциал роста",
  "Margin pressure": "Давление на маржу",
  "Restock needed": "Нужно пополнение",
  "Attention on efficiency": "Требуется внимание к эффективности",
  "Partially linked": "Данные связаны частично",
  "Demand remains stable": "Спрос остается стабильным",
  "Demand accelerating": "Спрос ускоряется",
  "Fast growth": "Быстрый рост",
  Growing: "Рост",
  Flat: "Без выраженного роста",
  "Active SKU": "Активные SKU",
  "Problem SKU": "SKU с рисками",
  "SKU at Risk": "SKU под риском",
  "Growth SKU": "SKU роста",
  "SKU Count": "Всего SKU"
};

export function localizeStatus(value?: string | null) {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (!normalized) {
    return "Нет данных";
  }
  return STATUS_LABELS[normalized] ?? KNOWN_TEXT_LABELS[value ?? ""] ?? value ?? "Нет данных";
}

export function localizeWorkspaceLabel(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (!normalized) {
    return "Платформа";
  }
  return WORKSPACE_LABELS[normalized] ?? value ?? "Платформа";
}

export function localizeRuntimeSource(source?: ApiRuntimeSource | string | null) {
  switch (source) {
    case "live":
      return "Данные обновлены";
    case "cache":
      return "Данные недавно обновлены";
    case "stale_cache":
    case "degraded":
      return "Данные частично недоступны";
    case "fallback":
      return "Повторите обновление позже";
    case "demo":
      return "Демо-режим";
    case "dev":
      return "Тестовый режим";
    default:
      return "Нет данных";
  }
}

export function localizeDiagnosticsLabel(diagnostics?: WorkspaceDiagnostics) {
  if (!diagnostics) {
    return "Нет данных";
  }
  if (diagnostics.degraded || diagnostics.stale) {
    return "Данные частично недоступны";
  }
  if (diagnostics.cached) {
    return "Данные недавно обновлены";
  }
  return localizeRuntimeSource(diagnostics.source);
}

export function localizeConfidence(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (normalized === "high") {
    return "Высокая";
  }
  if (normalized === "medium") {
    return "Средняя";
  }
  if (normalized === "low") {
    return "Низкая";
  }
  return "Нет данных";
}

export function localizeSeverity(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (normalized === "critical") {
    return "Критично";
  }
  if (normalized === "high") {
    return "Высокий приоритет";
  }
  if (normalized === "medium") {
    return "Средний приоритет";
  }
  if (normalized === "low") {
    return "Низкий приоритет";
  }
  if (normalized === "info") {
    return "Информация";
  }
  return "Нет данных";
}

export function localizePeriodLabel(value?: string | null) {
  const normalized = String(value ?? "").trim();
  if (!normalized) {
    return "Период не указан";
  }
  return PERIOD_LABELS[normalized] ?? KNOWN_TEXT_LABELS[normalized] ?? value ?? "Период не указан";
}

export function localizeKnownText(value?: string | null, fallback = "Нет данных") {
  const text = String(value ?? "").trim();
  if (!text) {
    return fallback;
  }
  if (KNOWN_TEXT_LABELS[text]) {
    return KNOWN_TEXT_LABELS[text];
  }
  if (/confidence$/i.test(text)) {
    return "Уверенность";
  }
  if (/backend|frontend|snapshot|placeholder|mock|runtime|source|api\./i.test(text)) {
    return fallback;
  }
  return text;
}

export function localizeSourceName(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (!normalized) {
    return "данные кабинета";
  }
  const mapped = WORKSPACE_LABELS[normalized];
  if (mapped) {
    return mapped.toLowerCase();
  }
  if (["backend", "placeholder", "executivebrief", "priorityactions", "api.alerts", "api.actions"].includes(normalized)) {
    return "данные кабинета";
  }
  return "данные кабинета";
}

export function humanizeErrorMessage(value?: string | null) {
  const text = String(value ?? "").trim();
  if (!text) {
    return "Не удалось загрузить данные. Попробуйте обновить страницу позже.";
  }
  if (text === "Backend is unreachable.") {
    return "Не удалось загрузить данные. Попробуйте обновить страницу позже.";
  }
  if (text.includes("API token")) {
    return "Данные временно недоступны. Проверьте подключение кабинета и повторите обновление позже.";
  }
  if (/backend|frontend|snapshot|placeholder|mock|runtime|source|api\./i.test(text)) {
    return "Не удалось загрузить данные. Попробуйте обновить страницу позже.";
  }
  return KNOWN_TEXT_LABELS[text] ?? text;
}

export function formatOptionalValue(value?: string | number | null, fallback = "Нет данных") {
  if (value === null || value === undefined) {
    return fallback;
  }

  const text = String(value).trim();
  if (!text) {
    return fallback;
  }

  const normalized = text.toLowerCase();
  if (["n/a", "na", "unknown", "pending", "-", "unavailable"].includes(normalized)) {
    return fallback;
  }

  return localizeKnownText(text, fallback);
}

export function localizeRoleLabel(value?: string | null) {
  switch (String(value ?? "").trim().toLowerCase()) {
    case "owner":
      return "Владелец";
    case "admin":
      return "Администратор";
    case "manager":
      return "Менеджер";
    case "analyst":
      return "Аналитик";
    case "viewer":
      return "Наблюдатель";
    default:
      return "Нет данных";
  }
}
