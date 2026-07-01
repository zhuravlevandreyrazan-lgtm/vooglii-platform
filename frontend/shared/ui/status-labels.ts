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
  HIGH: "Высокий",
  MEDIUM: "Средний",
  LOW: "Низкий"
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
      return "LIVE BACKEND";
    case "cache":
      return "LIVE CACHE";
    case "stale_cache":
    case "degraded":
      return "DEGRADED";
    case "fallback":
      return "Резервные данные";
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
    return "DEGRADED";
  }
  if (diagnostics.cached) {
    return "LIVE CACHE";
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

  return text;
}
