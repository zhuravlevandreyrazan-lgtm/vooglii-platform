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
  WATCH: "Под наблюдением",
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
  LOW: "Низкий уровень"
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
  health: "Оценка состояния",
  import: "Импорт",
  forecast: "Прогноз",
  restock: "Пополнение",
  sevenDays: "7 дней",
  thirtyDays: "30 дней",
  ninetyDays: "90 дней"
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
  Week: "Неделя",
  "Executive Brief": "Краткий вывод",
  Difference: "Расхождение",
  "Backend is unreachable.": "Не удалось загрузить данные. Попробуйте обновить страницу позже.",
  "Unable to load data": "Не удалось загрузить данные",
  "Empty state": "Нет данных",
  "Data for this block is not available yet.": "Данные для этого блока пока недоступны.",
  "Command Center": "Центр управления",
  "Source": "Источник",
  "Updated": "Обновлено",
  "Refresh snapshot": "Обновить данные",
  "Coming soon": "Раздел в подготовке"
};

export function localizeStatus(value?: string | null) {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (!normalized) {
    return "Нет данных";
  }
  return STATUS_LABELS[normalized] ?? value ?? "Нет данных";
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
      return "Резервный режим";
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
  return PERIOD_LABELS[normalized] ?? value ?? "Период не указан";
}

export function localizeKnownText(value?: string | null, fallback = "Нет данных") {
  const text = String(value ?? "").trim();
  if (!text) {
    return fallback;
  }
  return KNOWN_TEXT_LABELS[text] ?? text;
}

export function localizeSourceName(value?: string | null) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (!normalized) {
    return "источник не указан";
  }
  const mapped = WORKSPACE_LABELS[normalized];
  if (mapped) {
    return mapped.toLowerCase();
  }
  if (normalized === "backend") {
    return "данные кабинета";
  }
  if (normalized === "placeholder") {
    return "временный источник";
  }
  if (normalized === "system") {
    return "система";
  }
  if (normalized === "executivebrief" || normalized === "priorityactions" || normalized === "api.alerts" || normalized === "api.actions") {
    return "данные кабинета";
  }
  return value ?? "источник не указан";
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
  return text;
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
