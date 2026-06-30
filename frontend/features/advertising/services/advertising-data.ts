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
      label: "Advertising Spend",
      value: formatCurrency(68420),
      note: "Total ad spend from the current backend-ready advertising snapshot.",
      tone: "watch"
    },
    {
      key: "linkedSpend",
      label: "Linked Spend",
      value: formatCurrency(53600),
      note: "Spend successfully linked to attributable campaign-level analytics.",
      tone: "healthy"
    },
    {
      key: "unlinkedSpend",
      label: "Unlinked Spend",
      value: formatCurrency(14820),
      note: "Spend not fully attributable in the current advertising snapshot.",
      tone: "watch"
    },
    {
      key: "roas",
      label: "ROAS",
      value: "4.2x",
      note: "Backend-provided return on advertising spend.",
      tone: "healthy"
    },
    {
      key: "acos",
      label: "ACOS",
      value: formatPercent(23.8),
      note: "Backend-provided advertising cost of sales.",
      tone: "accent"
    },
    {
      key: "adsHealth",
      label: "Ads Health",
      value: "WATCH",
      note: "Overall advertising health status from the analytics engine.",
      tone: "watch"
    },
    {
      key: "trust",
      label: "Trust",
      value: "Medium",
      note: "Trust level inherited from backend advertising analytics readiness.",
      tone: "neutral"
    },
    {
      key: "status",
      label: "Status",
      value: "Attention on efficiency",
      note: "Current advertising operating status from the prepared snapshot.",
      tone: "watch"
    }
  ],
  recommendations: [
    {
      id: "ads-rec-1",
      campaign: "Search Cluster A",
      recommendation: "Reduce bids on low-intent queries",
      reason: "ROAS has weakened while spend continues to rise in this cluster.",
      expectedEffect: "Recover efficiency and protect contribution margin.",
      confidence: "Medium",
      severity: "high"
    },
    {
      id: "ads-rec-2",
      campaign: "Brand Retargeting",
      recommendation: "Increase spend gradually",
      reason: "This campaign maintains strong ROAS with stable attribution quality.",
      expectedEffect: "Capture additional profitable demand with limited downside risk.",
      confidence: "High",
      severity: "low"
    }
  ],
  alerts: [
    {
      id: "ads-alert-1",
      title: "Unlinked spend remains elevated",
      description: "A material share of spend is still not linked to attributable campaign analytics.",
      severity: "medium",
      source: "backend"
    },
    {
      id: "ads-alert-2",
      title: "Duplicate spend detected",
      description: "Duplicate spend needs review before campaign efficiency can be read with full confidence.",
      severity: "high",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "ads-timeline-1",
      title: "Advertising sync completed",
      description: "The latest ad account sync finished and prepared a new snapshot for the workspace.",
      period: "sync",
      severity: "info",
      source: "backend"
    },
    {
      id: "ads-timeline-2",
      title: "Latest analytics bundle loaded",
      description: "Advertising analytics from the current backend engine were refreshed.",
      period: "analytics",
      severity: "low",
      source: "backend"
    },
    {
      id: "ads-timeline-3",
      title: "Latest Ads Health evaluated",
      description: "Current Ads Health remains in watch mode due to efficiency and attribution pressure.",
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
      status: "Needs tuning",
      recommendation: "Reduce bids on low-intent queries"
    },
    {
      id: "ads-campaign-2",
      campaign: "Brand Retargeting",
      spend: 14280,
      revenue: 76140,
      roas: 5.3,
      acos: 18.8,
      status: "Scaling",
      recommendation: "Increase spend gradually"
    },
    {
      id: "ads-campaign-3",
      campaign: "Discovery Tests",
      spend: null,
      revenue: null,
      roas: null,
      acos: null,
      status: "Awaiting linkage",
      recommendation: "Wait for clearer attribution"
    }
  ],
  lastUpdated: "2026-06-30T13:00:00.000Z"
};

function normalizeMetric(metric: Partial<AdvertisingMetric>, index: number): AdvertisingMetric {
  return {
    key: metric.key ?? "advertisingSpend",
    label: metric.label ?? `Advertising Metric ${index + 1}`,
    value: metric.value ?? "n/a",
    note: metric.note ?? "No advertising detail is available for this metric yet.",
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
      adsHealth: raw.summary?.adsHealth ?? "Unknown",
      trust: raw.summary?.trust ?? "Unknown",
      status: raw.summary?.status ?? "Pending",
      trend: raw.summary?.trend ?? []
    },
    health: {
      adsHealth: raw.health?.adsHealth ?? "Unknown",
      linkability: raw.health?.linkability ?? null,
      duplicateSpend: raw.health?.duplicateSpend ?? null,
      linkedPercent: raw.health?.linkedPercent ?? null,
      coverage: raw.health?.coverage ?? null,
      status: raw.health?.status ?? "Pending"
    },
    metrics: (raw.metrics ?? []).map(normalizeMetric),
    recommendations:
      raw.recommendations?.length
        ? raw.recommendations
        : [
            {
              id: "ads-rec-fallback",
              campaign: "No campaign recommendation yet",
              recommendation: "Wait for backend recommendation payload",
              reason: "No campaign recommendation was returned in the current advertising snapshot.",
              expectedEffect: "Recommendation panel architecture stays ready for future backend integration.",
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
              title: "No advertising alerts available",
              description: "Backend did not return advertising alerts for the current snapshot.",
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
              title: "Advertising timeline is waiting for backend events",
              description: "No timeline events are available for the current advertising snapshot.",
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
              campaign: "Campaign data pending",
              spend: null,
              revenue: null,
              roas: null,
              acos: null,
              status: "No backend campaign list yet",
              recommendation: "Placeholder row keeps the UI ready for direct backend campaign payloads."
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
