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
  AdvertisingAlert,
  AdvertisingCampaign,
  AdvertisingHealth,
  AdvertisingMetric,
  AdvertisingRecommendation,
  AdvertisingSnapshot,
  AdvertisingSummary,
  AdvertisingTimelineEvent
} from "@/features/advertising/types";

type RawAdvertisingSnapshot = {
  summary?: Partial<AdvertisingSummary>;
  health?: Partial<AdvertisingHealth>;
  metrics?: Partial<AdvertisingMetric>[];
  recommendations?: AdvertisingRecommendation[];
  alerts?: AdvertisingAlert[];
  timeline?: AdvertisingTimelineEvent[];
  campaigns?: AdvertisingCampaign[];
  lastUpdated?: string | null;
};

const rawAdvertisingSnapshot: RawAdvertisingSnapshot = {
  summary: {
    advertisingSpend: 68420,
    linkedSpend: 53600,
    unlinkedSpend: 14820,
    roas: 4.2,
    acos: 23.8,
    adsHealth: "WATCH",
    trust: "Medium",
    status: "Attention on efficiency",
    trend: [
      { label: "W1", value: 18400 },
      { label: "W2", value: 20180 },
      { label: "W3", value: 19340 },
      { label: "W4", value: 22460 }
    ]
  },
  health: {
    adsHealth: "WATCH",
    linkability: 78,
    duplicateSpend: 4200,
    linkedPercent: 78,
    coverage: 86,
    status: "Partially linked"
  },
  metrics: [
    {
      key: "advertisingSpend",
      label: "Расходы на рекламу",
      value: formatCurrency(68420),
      note: "Расходы на рекламу за выбранный период.",
      tone: "watch"
    },
    {
      key: "linkedSpend",
      label: "Связанные расходы",
      value: formatCurrency(53600),
      note: "Расходы, которые уже связаны с аналитикой кампаний.",
      tone: "healthy"
    },
    {
      key: "unlinkedSpend",
      label: "Нераспределенные расходы",
      value: formatCurrency(14820),
      note: "Часть расходов пока не привязана к кампаниям.",
      tone: "watch"
    },
    {
      key: "roas",
      label: "ROAS",
      value: "4.2x",
      note: "Окупаемость рекламных расходов.",
      tone: "healthy"
    },
    {
      key: "acos",
      label: "ACOS",
      value: formatPercent(23.8),
      note: "Доля рекламных расходов в продажах.",
      tone: "accent"
    },
    {
      key: "adsHealth",
      label: "Состояние рекламы",
      value: "WATCH",
      note: "Сводная оценка рекламных метрик.",
      tone: "watch"
    },
    {
      key: "trust",
      label: "Надежность",
      value: "Medium",
      note: "Насколько полно собраны рекламные данные.",
      tone: "neutral"
    },
    {
      key: "status",
      label: "Статус",
      value: "Attention on efficiency",
      note: "Короткий вывод по текущей эффективности рекламы.",
      tone: "watch"
    }
  ],
  recommendations: [
    {
      id: "ads-rec-1",
      campaign: "Search Cluster A",
      recommendation: "Снизить ставки по низкоконверсионным запросам",
      reason: "ROAS снижается, а расходы в этом кластере продолжают расти.",
      expectedEffect: "Вернуть эффективность и защитить маржу.",
      confidence: "Medium",
      severity: "high"
    },
    {
      id: "ads-rec-2",
      campaign: "Brand Retargeting",
      recommendation: "Увеличивать бюджет постепенно",
      reason: "Кампания удерживает сильный ROAS и стабильную атрибуцию.",
      expectedEffect: "Поможет аккуратно нарастить прибыльный спрос.",
      confidence: "High",
      severity: "low"
    }
  ],
  alerts: [
    {
      id: "ads-alert-1",
      title: "Нераспределенные расходы остаются высокими",
      description: "Заметная часть рекламных расходов пока не связана с аналитикой кампаний.",
      severity: "medium",
      source: "backend"
    },
    {
      id: "ads-alert-2",
      title: "Найдены дублирующиеся расходы",
      description: "Проверьте дубли перед оценкой эффективности рекламных кампаний.",
      severity: "high",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "ads-timeline-1",
      title: "Синхронизация рекламного кабинета завершена",
      description: "В рабочее пространство загружены обновленные рекламные данные.",
      period: "sync",
      severity: "info",
      source: "backend"
    },
    {
      id: "ads-timeline-2",
      title: "Аналитика рекламы обновлена",
      description: "Появились свежие метрики по расходам и эффективности кампаний.",
      period: "analytics",
      severity: "low",
      source: "backend"
    },
    {
      id: "ads-timeline-3",
      title: "Рекламные метрики требуют внимания",
      description: "Эффективность и атрибуция части кампаний пока нестабильны.",
      period: "health",
      severity: "medium",
      source: "backend"
    }
  ],
  campaigns: [
    {
      id: "ads-campaign-1",
      campaign: "Search Cluster A",
      spend: 21950,
      revenue: 78600,
      roas: 3.6,
      acos: 27.9,
      status: "Требует настройки",
      recommendation: "Снизить ставки по низкоконверсионным запросам"
    },
    {
      id: "ads-campaign-2",
      campaign: "Brand Retargeting",
      spend: 14280,
      revenue: 76140,
      roas: 5.3,
      acos: 18.8,
      status: "Можно масштабировать",
      recommendation: "Увеличивать бюджет постепенно"
    },
    {
      id: "ads-campaign-3",
      campaign: "Discovery Tests",
      spend: null,
      revenue: null,
      roas: null,
      acos: null,
      status: "Ожидаем атрибуцию",
      recommendation: "Дождитесь накопления данных по атрибуции"
    }
  ],
  lastUpdated: "2026-06-30T13:00:00.000Z"
};

function normalizeMetric(metric: Partial<AdvertisingMetric>, index: number): AdvertisingMetric {
  return {
    key: metric.key ?? "advertisingSpend",
    label: localizeKnownText(metric.label, `Показатель ${index + 1}`),
    value: localizeKnownText(metric.value, "Нет данных"),
    note: localizeKnownText(metric.note, "Показатель появится после синхронизации."),
    tone: metric.tone ?? "neutral"
  };
}

export function normalizeAdvertisingSnapshot(
  raw: RawAdvertisingSnapshot,
  diagnostics = createFallbackDiagnostics()
): AdvertisingSnapshot {
  return {
    summary: {
      advertisingSpend: raw.summary?.advertisingSpend ?? null,
      linkedSpend: raw.summary?.linkedSpend ?? null,
      unlinkedSpend: raw.summary?.unlinkedSpend ?? null,
      roas: raw.summary?.roas ?? null,
      acos: raw.summary?.acos ?? null,
      adsHealth: localizeStatus(raw.summary?.adsHealth ?? "Unknown"),
      trust: localizeKnownText(raw.summary?.trust ?? "Unknown"),
      status: localizeKnownText(raw.summary?.status ?? "Pending"),
      trend: raw.summary?.trend ?? []
    },
    health: {
      adsHealth: localizeStatus(raw.health?.adsHealth ?? "Unknown"),
      linkability: raw.health?.linkability ?? null,
      duplicateSpend: raw.health?.duplicateSpend ?? null,
      linkedPercent: raw.health?.linkedPercent ?? null,
      coverage: raw.health?.coverage ?? null,
      status: localizeKnownText(raw.health?.status ?? "Pending")
    },
    metrics: (raw.metrics ?? []).map(normalizeMetric),
    recommendations:
      raw.recommendations?.length
        ? raw.recommendations
        : [
            {
              id: "ads-rec-fallback",
              campaign: "Рекомендации по кампаниям пока не готовы",
              recommendation: "Дождитесь обновления рекламных данных",
              reason: "Система пока не получила рекомендации по кампаниям.",
              expectedEffect: "Советы появятся после следующей синхронизации.",
              confidence: "Unknown",
              severity: "info"
            }
          ],
    alerts:
      raw.alerts?.length
        ? raw.alerts
        : [
            {
              id: "ads-alert-fallback",
              title: "Сигналы по рекламе пока не поступали",
              description: "После синхронизации здесь появятся важные предупреждения по рекламе.",
              severity: "info",
              source: "placeholder"
            }
          ],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "ads-timeline-fallback",
              title: "Лента рекламы обновится после синхронизации",
              description: "События по рекламным кампаниям появятся автоматически.",
              period: "sync",
              severity: "info",
              source: "placeholder"
            }
          ],
    campaigns:
      raw.campaigns?.length
        ? raw.campaigns
        : [
            {
              id: "ads-campaign-fallback",
              campaign: "Данные по кампаниям появятся после синхронизации",
              spend: null,
              revenue: null,
              roas: null,
              acos: null,
              status: "Нет данных",
              recommendation: "Показатели появятся после обновления рекламных данных."
            }
          ],
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getAdvertisingMockSnapshot() {
  return normalizeAdvertisingSnapshot(rawAdvertisingSnapshot);
}

function isRawAdvertisingSnapshot(value: unknown): value is RawAdvertisingSnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    (record.summary === undefined || getObjectField(record, "summary") !== undefined) &&
    (record.health === undefined || getObjectField(record, "health") !== undefined) &&
    (record.metrics === undefined || Array.isArray(record.metrics)) &&
    (record.recommendations === undefined || Array.isArray(record.recommendations)) &&
    (record.alerts === undefined || Array.isArray(record.alerts)) &&
    (record.timeline === undefined || Array.isArray(record.timeline)) &&
    (record.campaigns === undefined || Array.isArray(record.campaigns))
  );
}

export async function fetchAdvertisingSnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.advertising, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.advertising, "Advertising");

  if (!isRawAdvertisingSnapshot(record)) {
    throw new ApiError("Advertising API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.advertising
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeAdvertisingSnapshot(
    {
      ...record,
      metrics: getArrayField(record, "metrics"),
      recommendations: getArrayField(record, "recommendations"),
      alerts: getArrayField(record, "alerts"),
      timeline: getArrayField(record, "timeline"),
      campaigns: getArrayField(record, "campaigns")
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
