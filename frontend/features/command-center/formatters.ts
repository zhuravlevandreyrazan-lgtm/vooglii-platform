import type { ExecutiveTimelinePeriod, ExecutiveTimelineSeverity } from "@/features/command-center/executive-timeline-types";
import type { KpiMetric } from "@/features/command-center/kpi-types";
import type { PriorityActionSeverity } from "@/features/command-center/priority-actions-types";

import { localizePeriodLabel, localizeSeverity } from "@/shared/ui/status-labels";

const FALLBACK_TEXT = "Нет данных";

export function formatCurrency(value?: number | null, currency = "RUB") {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return FALLBACK_TEXT;
  }

  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(value);
}

export function formatPercent(value?: number | null, fractionDigits = 1) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return FALLBACK_TEXT;
  }

  return `${value.toFixed(fractionDigits)}%`;
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return undefined;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return undefined;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

export function formatKpiValue(metric?: KpiMetric | null) {
  if (!metric || metric.state !== "ready") {
    return FALLBACK_TEXT;
  }

  return metric.value || FALLBACK_TEXT;
}

export function formatSeverityLabel(
  value?: PriorityActionSeverity | ExecutiveTimelineSeverity | null
) {
  if (!value) {
    return FALLBACK_TEXT;
  }

  return localizeSeverity(value);
}

export function formatPeriodLabel(period: ExecutiveTimelinePeriod) {
  return localizePeriodLabel(period);
}
