import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  getArrayField,
  getObjectField,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";
import { localizeKnownText, localizeStatus } from "@/shared/ui/status-labels";
import type {
  FinanceAlert,
  FinanceDifference,
  FinanceMetric,
  FinanceQuality,
  FinanceSnapshot,
  FinanceSummary
} from "@/features/finance/types";

type RawFinanceSnapshot = {
  summary?: Partial<FinanceSummary>;
  quality?: Partial<FinanceQuality>;
  difference?: Partial<FinanceDifference>;
  metrics?: Partial<FinanceMetric>[];
  alerts?: FinanceAlert[];
  timeline?: FinanceSnapshot["timeline"];
  lastUpdated?: string | null;
};

const rawFinanceSnapshot: RawFinanceSnapshot = {
  summary: {
    operatingProfit: 105690,
    officialProfit: null,
    difference: 110805,
    health: "DEGRADED",
    trustScore: 35,
    status: "Требуется внимание"
  },
  quality: {
    coverage: 81,
    residualUsage: "Используется резервная модель расчета",
    trustScore: 35,
    confidence: "Low",
    health: "DEGRADED"
  },
  difference: {
    operatingProfit: 105690,
    officialProfit: null,
    difference: 110805,
    differencePercent: 125.6,
    reason: "Компоненты финансового отчета частично пересекаются, поэтому официальная прибыль пока не подтверждена построчно.",
    explanation: "Пока безопаснее использовать операционную прибыль как основной управленческий показатель."
  },
  metrics: [
    {
      key: "operatingProfit",
      label: "Операционная прибыль",
      value: formatCurrency(105690),
      note: "Основной управленческий показатель прибыли.",
      tone: "healthy"
    },
    {
      key: "officialProfit",
      label: "Официальная прибыль",
      value: "Нет данных",
      note: "Официальная прибыль пока не подтверждена полностью.",
      tone: "neutral"
    },
    {
      key: "profitDifference",
      label: "Расхождение",
      value: formatCurrency(110805),
      note: "Разница между управленческой и официальной прибылью.",
      tone: "watch"
    },
    {
      key: "financeHealth",
      label: "Состояние финансов",
      value: "DEGRADED",
      note: "Финансовые данные доступны частично и требуют проверки.",
      tone: "watch"
    },
    {
      key: "trustScore",
      label: "Надежность",
      value: "35/100",
      note: "Чем ниже значение, тем осторожнее нужно трактовать показатели.",
      tone: "risk"
    },
    {
      key: "coverage",
      label: "Покрытие",
      value: formatPercent(81, 0),
      note: "Доля финансовых данных, доступных для сверки.",
      tone: "accent"
    },
    {
      key: "confidence",
      label: "Уверенность",
      value: "Low",
      note: "Уровень уверенности зависит от полноты и качества данных.",
      tone: "watch"
    },
    {
      key: "residualModel",
      label: "Модель расчета",
      value: "Используется резервная модель расчета",
      note: "Применяется безопасная логика для неполного покрытия данных.",
      tone: "neutral"
    },
    {
      key: "income",
      label: "Доходы",
      value: formatCurrency(311708),
      note: "Доходная часть финансовой сводки.",
      tone: "healthy"
    },
    {
      key: "expenses",
      label: "Расходы",
      value: formatCurrency(206018),
      note: "Расходная часть финансовой сводки.",
      tone: "watch"
    }
  ],
  alerts: [
    {
      id: "finance-alert-1",
      title: "Официальная прибыль пока не подтверждена",
      description: "Покрытия Finance API пока недостаточно для полной сверки официальной прибыли.",
      severity: "high",
      source: "backend"
    },
    {
      id: "finance-alert-2",
      title: "Финансовые компоненты требуют проверки",
      description: "Некоторые показатели пересекаются и влияют на итоговое расхождение.",
      severity: "medium",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "finance-timeline-1",
      title: "Финансовая сводка обновлена",
      description: "В разделе появились последние финансовые показатели.",
      period: "latest",
      severity: "info",
      source: "backend"
    },
    {
      id: "finance-timeline-2",
      title: "Проведена сверка прибыли",
      description: "Операционная прибыль остается основным управленческим ориентиром.",
      period: "audit",
      severity: "medium",
      source: "backend"
    },
    {
      id: "finance-timeline-3",
      title: "Синхронизация финансов завершена",
      description: "Данные обновлены, но покрытие пока неполное.",
      period: "sync",
      severity: "low",
      source: "backend"
    }
  ],
  lastUpdated: "2026-06-30T12:30:00.000Z"
};

function normalizeMetric(metric: Partial<FinanceMetric>, index: number): FinanceMetric {
  return {
    key: metric.key ?? "operatingProfit",
    label: localizeKnownText(metric.label, `Показатель ${index + 1}`),
    value: localizeKnownText(metric.value, "Нет данных"),
    note: localizeKnownText(metric.note, "Показатель появится после обновления данных."),
    tone: metric.tone ?? "neutral"
  };
}

export function normalizeFinanceSnapshot(
  raw: RawFinanceSnapshot,
  diagnostics = createFallbackDiagnostics()
): FinanceSnapshot {
  return {
    summary: {
      operatingProfit: raw.summary?.operatingProfit ?? null,
      officialProfit: raw.summary?.officialProfit ?? null,
      difference: raw.summary?.difference ?? null,
      health: localizeStatus(raw.summary?.health ?? "Unknown"),
      trustScore: raw.summary?.trustScore ?? null,
      status: localizeKnownText(raw.summary?.status ?? "Pending")
    },
    quality: {
      coverage: raw.quality?.coverage ?? null,
      residualUsage: localizeKnownText(raw.quality?.residualUsage ?? "Нет данных по модели расчета."),
      trustScore: raw.quality?.trustScore ?? null,
      confidence: localizeKnownText(raw.quality?.confidence ?? "Unknown"),
      health: localizeStatus(raw.quality?.health ?? "Unknown")
    },
    difference: {
      operatingProfit: raw.difference?.operatingProfit ?? raw.summary?.operatingProfit ?? null,
      officialProfit: raw.difference?.officialProfit ?? raw.summary?.officialProfit ?? null,
      difference: raw.difference?.difference ?? raw.summary?.difference ?? null,
      differencePercent: raw.difference?.differencePercent ?? null,
      reason: localizeKnownText(raw.difference?.reason, "Расшифровка расхождения появится позже."),
      explanation: raw.difference?.explanation ? localizeKnownText(raw.difference.explanation) : null
    },
    metrics: (raw.metrics ?? []).map(normalizeMetric),
    alerts:
      raw.alerts?.length
        ? raw.alerts
        : [
            {
              id: "finance-alert-fallback",
              title: "Финансовые сигналы пока не поступали",
              description: "После синхронизации здесь появятся важные финансовые предупреждения.",
              severity: "info",
              source: "placeholder"
            }
          ],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "finance-timeline-fallback",
              title: "Лента финансов обновится после синхронизации",
              description: "События по финансам появятся автоматически.",
              period: "latest",
              severity: "info",
              source: "placeholder"
            }
          ],
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getFinanceMockSnapshot() {
  return normalizeFinanceSnapshot(rawFinanceSnapshot);
}

function isRawFinanceSnapshot(value: unknown): value is RawFinanceSnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  const summary = record.summary;
  const quality = record.quality;
  const difference = record.difference;
  const metrics = record.metrics;
  const alerts = record.alerts;
  const timeline = record.timeline;

  return (
    (summary === undefined || getObjectField(record, "summary") !== undefined) &&
    (quality === undefined || getObjectField(record, "quality") !== undefined) &&
    (difference === undefined || getObjectField(record, "difference") !== undefined) &&
    (metrics === undefined || Array.isArray(metrics)) &&
    (alerts === undefined || Array.isArray(alerts)) &&
    (timeline === undefined || Array.isArray(timeline))
  );
}

export async function fetchFinanceSnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.finance, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.finance, "Finance");

  if (!isRawFinanceSnapshot(record)) {
    throw new ApiError("Finance API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.finance
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeFinanceSnapshot(
    {
      ...record,
      metrics: getArrayField(record, "metrics"),
      alerts: getArrayField(record, "alerts"),
      timeline: getArrayField(record, "timeline")
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
