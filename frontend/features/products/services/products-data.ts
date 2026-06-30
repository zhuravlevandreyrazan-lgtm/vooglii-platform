import type {
  ProductAlert,
  ProductCard,
  ProductHistory,
  ProductRecommendation,
  ProductSnapshot,
  ProductTimeline
} from "@/features/products/types";
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

type RawProductSnapshot = {
  summary?: Partial<ProductSnapshot["summary"]>;
  products?: ProductCard[];
  recommendations?: ProductRecommendation[];
  history?: ProductHistory[];
  inventoryPreview?: ProductCard[];
  alerts?: ProductAlert[];
  timeline?: ProductTimeline[];
  actions?: ProductSnapshot["actions"];
  lastUpdated?: string | null;
};

const rawProductSnapshot: RawProductSnapshot = {
  summary: {
    skuCount: 48,
    activeSku: 41,
    problemSku: 7,
    riskSku: 5,
    growthSku: 11,
    lastUpdated: "2026-06-30T13:30:00.000Z"
  },
  products: [
    {
      sku: "VOO-TS-001",
      name: "Thermal Bottle 750ml",
      metrics: {
        revenue: 82340,
        profit: 29120,
        margin: 35.4,
        roas: 4.8,
        acos: 20.9,
        stock: 412,
        daysLeft: 23
      },
      health: {
        health: "Strong",
        status: "Scaling",
        abc: "A",
        xyz: "X",
        forecast: "Stable demand",
        riskLevel: "Low"
      },
      status: {
        label: "Scaling",
        tone: "accent"
      },
      recommendation: "Increase stock coverage before the next promotion cycle.",
      trend: "Growing",
      warehouse: "Kolедino"
    },
    {
      sku: "VOO-BG-018",
      name: "Travel Organizer Set",
      metrics: {
        revenue: 69480,
        profit: 20660,
        margin: 29.7,
        roas: 3.4,
        acos: 29.4,
        stock: 186,
        daysLeft: 11
      },
      health: {
        health: "Watch",
        status: "Margin pressure",
        abc: "A",
        xyz: "Y",
        forecast: "Demand remains stable",
        riskLevel: "Medium"
      },
      status: {
        label: "Margin pressure",
        tone: "watch"
      },
      recommendation: "Reduce inefficient traffic and protect margin before scaling.",
      trend: "Flat",
      warehouse: "Elektrougli"
    },
    {
      sku: "VOO-HM-203",
      name: "Kitchen Storage Bundle",
      metrics: {
        revenue: 51420,
        profit: 19410,
        margin: 37.7,
        roas: null,
        acos: null,
        stock: 54,
        daysLeft: 5
      },
      health: {
        health: "Risk",
        status: "Restock needed",
        abc: "B",
        xyz: "X",
        forecast: "Demand is accelerating",
        riskLevel: "High"
      },
      status: {
        label: "Restock needed",
        tone: "risk"
      },
      recommendation: "Prioritize replenishment and monitor demand daily.",
      trend: "Fast growth",
      warehouse: "Kazan"
    }
  ],
  recommendations: [
    {
      id: "product-rec-1",
      sku: "VOO-HM-203",
      recommendation: "Restock within 3 days",
      reason: "Days left are low while demand remains strong.",
      priority: "critical",
      confidence: "High",
      expectedEffect: "Avoid stockout and protect revenue continuity."
    },
    {
      id: "product-rec-2",
      sku: "VOO-BG-018",
      recommendation: "Audit paid traffic efficiency",
      reason: "Margin and ACOS suggest weak advertising quality.",
      priority: "high",
      confidence: "Medium",
      expectedEffect: "Recover contribution margin on a high-volume SKU."
    }
  ],
  history: [
    {
      period: "today",
      sales: 21480,
      advertising: 4210,
      note: "Current-day SKU revenue and ad activity snapshot."
    },
    {
      period: "sevenDays",
      sales: 148300,
      advertising: 23640,
      note: "Seven-day product sales and advertising summary."
    },
    {
      period: "thirtyDays",
      sales: 411800,
      advertising: 68420,
      note: "Thirty-day product performance rollup."
    },
    {
      period: "ninetyDays",
      sales: 1094700,
      advertising: 183600,
      note: "Ninety-day long-range product trend rollup."
    }
  ],
  inventoryPreview: [],
  alerts: [
    {
      id: "product-alert-1",
      title: "Out-of-stock risk on a growing SKU",
      description: "At least one SKU has low days left while demand remains strong.",
      severity: "high",
      source: "backend"
    },
    {
      id: "product-alert-2",
      title: "Margin pressure on key assortment",
      description: "One of the top revenue SKUs shows weaker profitability quality.",
      severity: "medium",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "product-timeline-1",
      title: "Latest product sync completed",
      description: "Product intelligence snapshot has been refreshed from backend-ready analytics.",
      period: "sync",
      severity: "info",
      source: "backend"
    },
    {
      id: "product-timeline-2",
      title: "Latest SKU audit recorded",
      description: "Current SKU health and action plan were updated in the product snapshot.",
      period: "audit",
      severity: "medium",
      source: "backend"
    },
    {
      id: "product-timeline-3",
      title: "Latest forecast updated",
      description: "Backend-ready forecast values were refreshed for product planning.",
      period: "forecast",
      severity: "low",
      source: "backend"
    }
  ],
  actions: [
    {
      id: "product-action-1",
      sku: "VOO-HM-203",
      action: "Restock urgently",
      status: "Open"
    }
  ],
  lastUpdated: "2026-06-30T13:30:00.000Z"
};

function emptyProductCard(): ProductCard {
  return {
    sku: "SKU-PENDING",
    name: "Product data pending",
    metrics: {
      revenue: null,
      profit: null,
      margin: null,
      roas: null,
      acos: null,
      stock: null,
      daysLeft: null
    },
    health: {
      health: "Unknown",
      status: "Pending backend data",
      abc: "n/a",
      xyz: "n/a",
      forecast: "No forecast yet",
      riskLevel: "Unknown"
    },
    status: {
      label: "Pending",
      tone: "neutral"
    },
    recommendation: "Placeholder row keeps the Products UI ready for direct backend integration.",
    trend: "Unknown",
    warehouse: "n/a"
  };
}

export function normalizeProductSnapshot(
  raw: RawProductSnapshot,
  diagnostics = createFallbackDiagnostics()
): ProductSnapshot {
  const fallbackCard = emptyProductCard();

  return {
    summary: {
      skuCount: raw.summary?.skuCount ?? 0,
      activeSku: raw.summary?.activeSku ?? 0,
      problemSku: raw.summary?.problemSku ?? 0,
      riskSku: raw.summary?.riskSku ?? 0,
      growthSku: raw.summary?.growthSku ?? 0,
      lastUpdated: raw.summary?.lastUpdated ?? raw.lastUpdated ?? null
    },
    products: raw.products?.length ? raw.products : [fallbackCard],
    recommendations:
      raw.recommendations?.length
        ? raw.recommendations
        : [
            {
              id: "product-rec-fallback",
              sku: "No SKU recommendation yet",
              recommendation: "Wait for backend action plan",
              reason: "No SKU action plan was returned in the current product snapshot.",
              priority: "info",
              confidence: "Unknown",
              expectedEffect: "Recommendations panel remains ready for direct backend payloads."
            }
          ],
    history:
      raw.history?.length
        ? raw.history
        : [
            {
              period: "today",
              sales: null,
              advertising: null,
              note: "Historical data is not available yet."
            }
          ],
    inventoryPreview: raw.inventoryPreview?.length ? raw.inventoryPreview : [fallbackCard],
    alerts:
      raw.alerts?.length
        ? raw.alerts
        : [
            {
              id: "product-alert-fallback",
              title: "No product alerts available",
              description: "Backend did not return product alerts for the current snapshot.",
              severity: "info",
              source: "placeholder"
            }
          ],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "product-timeline-fallback",
              title: "Product timeline is waiting for backend events",
              description: "No timeline entries are available yet.",
              period: "sync",
              severity: "info",
              source: "placeholder"
            }
          ],
    actions: raw.actions ?? [],
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getProductsMockSnapshot() {
  return normalizeProductSnapshot(rawProductSnapshot);
}

function isRawProductSnapshot(value: unknown): value is RawProductSnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    (record.summary === undefined || getObjectField(record, "summary") !== undefined) &&
    (record.products === undefined || Array.isArray(record.products)) &&
    (record.recommendations === undefined || Array.isArray(record.recommendations)) &&
    (record.history === undefined || Array.isArray(record.history)) &&
    (record.inventoryPreview === undefined || Array.isArray(record.inventoryPreview)) &&
    (record.alerts === undefined || Array.isArray(record.alerts)) &&
    (record.timeline === undefined || Array.isArray(record.timeline)) &&
    (record.actions === undefined || Array.isArray(record.actions))
  );
}

export async function fetchProductsSnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.products, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.products, "Products");

  if (!isRawProductSnapshot(record)) {
    throw new ApiError("Products API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.products
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeProductSnapshot(
    {
      ...record,
      products: getArrayField(record, "products"),
      recommendations: getArrayField(record, "recommendations"),
      history: getArrayField(record, "history"),
      inventoryPreview: getArrayField(record, "inventoryPreview"),
      alerts: getArrayField(record, "alerts"),
      timeline: getArrayField(record, "timeline"),
      actions: getArrayField(record, "actions")
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
