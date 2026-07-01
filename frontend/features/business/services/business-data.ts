import type { BusinessPeriodKey, BusinessSnapshot, BusinessTrend } from "@/features/business/types";
import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  getObjectField,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";

type RawBusinessSnapshot = {
  summary?: Partial<BusinessSnapshot["summary"]>;
  trends?: Partial<BusinessSnapshot["trends"]>;
  healthScore?: number;
  healthStatus?: string;
  periods?: Partial<Record<BusinessPeriodKey, Partial<BusinessTrend>>>;
  topProducts?: BusinessSnapshot["topProducts"];
  generatedAt?: string | null;
};

const PERIOD_LABELS: Record<BusinessPeriodKey, string> = {
  today: "Today",
  yesterday: "Yesterday",
  sevenDays: "7 Days",
  thirtyDays: "30 Days"
};

const rawBusinessSnapshot: RawBusinessSnapshot = {
  summary: {
    revenue: 311708,
    profit: 105690,
    margin: 33.9,
    orders: 1284,
    returns: 52,
    averageOrderValue: 243,
    unitsSold: 1678
  },
  trends: {
    revenue: 8.4,
    profit: -2.1,
    margin: -1.6,
    returns: 12.5
  },
  healthScore: 78,
  healthStatus: "Growth with pressure",
  periods: {
    today: {
      revenue: 42310,
      profit: 13860,
      margin: 32.8,
      orders: 169,
      returns: 6,
      averageOrderValue: 250,
      unitsSold: 224
    },
    yesterday: {
      revenue: 40120,
      profit: 14110,
      margin: 35.2,
      orders: 161,
      returns: 5,
      averageOrderValue: 249,
      unitsSold: 215
    },
    sevenDays: {
      revenue: 203550,
      profit: 67920,
      margin: 33.4,
      orders: 826,
      returns: 31,
      averageOrderValue: 246,
      unitsSold: 1085
    },
    thirtyDays: {
      revenue: 311708,
      profit: 105690,
      margin: 33.9,
      orders: 1284,
      returns: 52,
      averageOrderValue: 243,
      unitsSold: 1678
    }
  },
  topProducts: [
    {
      sku: "VOO-TS-001",
      title: "Thermal Bottle 750ml",
      revenue: 82340,
      profit: 29120,
      margin: 35.4,
      status: "Stable"
    },
    {
      sku: "VOO-BG-018",
      title: "Travel Organizer Set",
      revenue: 69480,
      profit: 20660,
      margin: 29.7,
      status: "Margin pressure"
    },
    {
      sku: "VOO-HM-203",
      title: "Kitchen Storage Bundle",
      revenue: 51420,
      profit: 19410,
      margin: 37.7,
      status: "Scaling"
    }
  ],
  generatedAt: "2026-06-30T12:00:00.000Z"
};

function getEmptyTrend(key: BusinessPeriodKey): BusinessTrend {
  return {
    key,
    label: PERIOD_LABELS[key],
    revenue: null,
    profit: null,
    margin: null,
    orders: null,
    returns: null,
    averageOrderValue: null,
    unitsSold: null
  };
}

function normalizeTrend(key: BusinessPeriodKey, trend?: Partial<BusinessTrend>): BusinessTrend {
  const empty = getEmptyTrend(key);
  return {
    ...empty,
    ...trend,
    revenue: trend?.revenue ?? empty.revenue,
    profit: trend?.profit ?? empty.profit,
    margin: trend?.margin ?? empty.margin,
    orders: trend?.orders ?? empty.orders,
    returns: trend?.returns ?? empty.returns,
    averageOrderValue: trend?.averageOrderValue ?? empty.averageOrderValue,
    unitsSold: trend?.unitsSold ?? empty.unitsSold
  };
}

export function normalizeBusinessSnapshot(
  raw: RawBusinessSnapshot,
  diagnostics = createFallbackDiagnostics()
): BusinessSnapshot {
  const revenue = raw.summary?.revenue ?? null;
  const orders = raw.summary?.orders ?? null;
  const profit = raw.summary?.profit ?? null;
  const margin = raw.summary?.margin ?? (revenue !== null && profit !== null && revenue > 0 ? (profit / revenue) * 100 : null);
  const averageOrderValue =
    raw.summary?.averageOrderValue ?? (orders !== null && orders > 0 && revenue !== null ? revenue / orders : null);

  return {
    summary: {
      revenue,
      profit,
      margin,
      orders,
      returns: raw.summary?.returns ?? null,
      averageOrderValue,
      unitsSold: raw.summary?.unitsSold ?? null
    },
    trends: {
      revenue: raw.trends?.revenue ?? null,
      profit: raw.trends?.profit ?? null,
      margin: raw.trends?.margin ?? null,
      returns: raw.trends?.returns ?? null
    },
    healthScore: raw.healthScore ?? undefined,
    healthStatus: raw.healthStatus ?? "Unknown",
    periods: {
      today: normalizeTrend("today", raw.periods?.today),
      yesterday: normalizeTrend("yesterday", raw.periods?.yesterday),
      sevenDays: normalizeTrend("sevenDays", raw.periods?.sevenDays),
      thirtyDays: normalizeTrend("thirtyDays", raw.periods?.thirtyDays)
    },
    topProducts: raw.topProducts ?? [],
    generatedAt: raw.generatedAt ?? null,
    diagnostics
  };
}

export function getBusinessMockSnapshot() {
  return normalizeBusinessSnapshot(rawBusinessSnapshot);
}

function isRawBusinessSnapshot(value: unknown): value is RawBusinessSnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  const summary = record.summary;
  const trends = record.trends;
  const periods = record.periods;

  return (
    (summary === undefined || getObjectField(record, "summary") !== undefined) &&
    (trends === undefined || getObjectField(record, "trends") !== undefined) &&
    (periods === undefined || getObjectField(record, "periods") !== undefined)
  );
}

export async function fetchBusinessSnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.business, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.business, "Business");

  if (!isRawBusinessSnapshot(record)) {
    throw new ApiError("Business API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.business
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeBusinessSnapshot(record, buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" }));
}
