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
    status: "Attention required"
  },
  quality: {
    coverage: 81,
    residualUsage: "Residual bridge active",
    trustScore: 35,
    confidence: "Low",
    health: "DEGRADED"
  },
  difference: {
    operatingProfit: 105690,
    officialProfit: null,
    difference: 110805,
    differencePercent: 125.6,
    reason: "Finance components overlap and official profit cannot yet be confirmed row-by-row.",
    explanation: "Operating profit remains the recommended management metric until a fuller finance report is available."
  },
  metrics: [
    {
      key: "operatingProfit",
      label: "Operating Profit",
      value: formatCurrency(105690),
      note: "Primary management profit metric from the safe operating model.",
      tone: "healthy"
    },
    {
      key: "officialProfit",
      label: "Official Profit",
      value: "Unavailable",
      note: "Backend flags official profit as not fully confirmed by Finance API coverage.",
      tone: "neutral"
    },
    {
      key: "profitDifference",
      label: "Profit Difference",
      value: formatCurrency(110805),
      note: "Difference between operating and backend-official finance representations.",
      tone: "watch"
    },
    {
      key: "financeHealth",
      label: "Finance Health",
      value: "DEGRADED",
      note: "Finance model is safe, but not yet ideal for official-profit confirmation.",
      tone: "watch"
    },
    {
      key: "trustScore",
      label: "Trust Score",
      value: "35/100",
      note: "Lower trust means stronger caution for official finance interpretation.",
      tone: "risk"
    },
    {
      key: "coverage",
      label: "Coverage",
      value: formatPercent(81, 0),
      note: "Coverage of compatible finance data available for reconciliation.",
      tone: "accent"
    },
    {
      key: "confidence",
      label: "Confidence",
      value: "Low",
      note: "Confidence is inherited from the current finance health and trust status.",
      tone: "watch"
    },
    {
      key: "residualModel",
      label: "Residual Model",
      value: "Residual bridge active",
      note: "Residual model is used as a safe bridge for incomplete finance coverage.",
      tone: "neutral"
    },
    {
      key: "income",
      label: "Income",
      value: formatCurrency(311708),
      note: "Income-side figure received from the prepared finance snapshot.",
      tone: "healthy"
    },
    {
      key: "expenses",
      label: "Expenses",
      value: formatCurrency(206018),
      note: "Expense-side figure prepared in the normalized finance snapshot.",
      tone: "watch"
    }
  ],
  alerts: [
    {
      id: "finance-alert-1",
      title: "Official profit is not fully confirmed",
      description: "Finance API coverage is not yet sufficient for a row-compatible official profit confirmation.",
      severity: "high",
      source: "backend"
    },
    {
      id: "finance-alert-2",
      title: "Difference remains overexplained",
      description: "Current finance explanations exceed 100% coverage, which points to overlapping components.",
      severity: "medium",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "finance-timeline-1",
      title: "Latest finance snapshot updated",
      description: "The finance workspace has received the latest normalized finance snapshot.",
      period: "latest",
      severity: "info",
      source: "backend"
    },
    {
      id: "finance-timeline-2",
      title: "Latest profit audit recorded",
      description: "Safe reconciliation confirms operational profit as the preferred management metric.",
      period: "audit",
      severity: "medium",
      source: "backend"
    },
    {
      id: "finance-timeline-3",
      title: "Latest finance sync finished",
      description: "Finance sync completed with degraded but usable coverage.",
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
    label: metric.label ?? `Metric ${index + 1}`,
    value: metric.value ?? "n/a",
    note: metric.note ?? "No detail is available for this finance metric yet.",
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
      health: raw.summary?.health ?? "Unknown",
      trustScore: raw.summary?.trustScore ?? null,
      status: raw.summary?.status ?? "Pending"
    },
    quality: {
      coverage: raw.quality?.coverage ?? null,
      residualUsage: raw.quality?.residualUsage ?? "No residual usage detail available.",
      trustScore: raw.quality?.trustScore ?? null,
      confidence: raw.quality?.confidence ?? "Unknown",
      health: raw.quality?.health ?? "Unknown"
    },
    difference: {
      operatingProfit: raw.difference?.operatingProfit ?? raw.summary?.operatingProfit ?? null,
      officialProfit: raw.difference?.officialProfit ?? raw.summary?.officialProfit ?? null,
      difference: raw.difference?.difference ?? raw.summary?.difference ?? null,
      differencePercent: raw.difference?.differencePercent ?? null,
      reason: raw.difference?.reason ?? "Difference explanation is not available from backend yet.",
      explanation: raw.difference?.explanation ?? null
    },
    metrics: (raw.metrics ?? []).map(normalizeMetric),
    alerts:
      raw.alerts?.length
        ? raw.alerts
        : [
            {
              id: "finance-alert-fallback",
              title: "No finance alerts available",
              description: "Backend did not return finance alerts for the current snapshot.",
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
              title: "Finance timeline is waiting for backend events",
              description: "No finance timeline entries are available yet.",
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
