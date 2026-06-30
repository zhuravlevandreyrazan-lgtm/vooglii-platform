import {
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
  ProductAction,
  ProductAdvertising,
  ProductDeepLink,
  ProductDetailsSnapshot,
  ProductEvidence,
  ProductFinance,
  ProductForecast,
  ProductHistory,
  ProductInsight,
  ProductInventory,
  ProductOverview,
  ProductRecommendation,
  ProductSales,
  ProductTimeline
} from "@/features/product-details/types";

type RawProductDetailsSnapshot = {
  overview?: Partial<ProductOverview>;
  sales?: Partial<ProductSales>;
  finance?: Partial<ProductFinance>;
  advertising?: Partial<ProductAdvertising>;
  inventory?: Partial<ProductInventory>;
  forecast?: Partial<ProductForecast>;
  history?: ProductHistory[];
  recommendations?: ProductRecommendation[];
  timeline?: ProductTimeline[];
  insight?: Partial<ProductInsight> & { evidence?: ProductEvidence[] };
  quickActions?: ProductAction[];
  deepLinks?: ProductDeepLink[];
  lastUpdated?: string | null;
  runtime?: Record<string, unknown>;
};

function buildFallbackDeepLinks(sku: string): ProductDeepLink[] {
  return [
    { id: "advertising", label: "Advertising", href: "/advertising", description: `Campaign context for ${sku}.` },
    { id: "inventory", label: "Inventory", href: `/inventory/${sku}`, description: `Inventory drilldown for ${sku}.` },
    { id: "finance", label: "Finance", href: "/finance", description: `Profitability workspace context for ${sku}.` },
    { id: "advisor", label: "Advisor", href: "/advisor", description: `Advisor recommendations related to ${sku}.` },
    { id: "reports", label: "Reports", href: "/reports", description: `Exports and report center for ${sku}.` },
    { id: "executive", label: "Executive", href: "/executive", description: "Executive summary and leadership context." },
    { id: "business", label: "Business", href: "/business", description: "Business KPI context for this product family." }
  ];
}

function createMockProductDetailsSnapshot(sku: string): RawProductDetailsSnapshot {
  return {
    overview: {
      sku,
      name: `Product ${sku}`,
      imageUrl: null,
      category: "Marketplace assortment",
      brand: "VOOGLII",
      vendorCode: `${sku}-VC`,
      status: {
        label: "Operational review",
        tone: "accent"
      },
      health: "Watch",
      healthScore: 72,
      abc: "A",
      xyz: "Y"
    },
    sales: {
      revenue: 69480,
      orders: 312,
      units: 338,
      averagePrice: 206,
      trend: "Stable demand with selective upside."
    },
    finance: {
      profit: 20660,
      margin: 29.7,
      expenses: 48820,
      officialProfit: null,
      difference: null
    },
    advertising: {
      spend: 20440,
      roas: 3.4,
      acos: 29.4,
      campaignCount: 4,
      adsHealth: "Watch"
    },
    inventory: {
      stock: 186,
      reserved: 19,
      available: 167,
      daysLeft: 11,
      forecast: "Demand remains stable for the next replenishment window.",
      warehouse: "Elektrougli"
    },
    forecast: {
      summary: "Forecast payload is represented as backend-ready summary text without frontend calculations.",
      confidence: "Medium",
      nextReorderDate: null
    },
    history: [
      {
        period: "today",
        revenue: 21480,
        profit: 6410,
        orders: 42,
        note: "Current-day performance snapshot."
      },
      {
        period: "sevenDays",
        revenue: 148300,
        profit: 42110,
        orders: 211,
        note: "Seven-day rollup from the current backend-ready snapshot."
      },
      {
        period: "thirtyDays",
        revenue: 411800,
        profit: 122430,
        orders: 612,
        note: "Thirty-day product history without frontend chart calculations."
      },
      {
        period: "ninetyDays",
        revenue: 1094700,
        profit: 312700,
        orders: 1714,
        note: "Ninety-day performance history placeholder for future chart expansion."
      }
    ],
    recommendations: [
      {
        id: "rec-1",
        priority: "high",
        reason: "Margin pressure appears alongside mixed advertising efficiency.",
        expectedEffect: "Recover contribution profit before the next scale-up cycle.",
        confidence: "Medium"
      },
      {
        id: "rec-2",
        priority: "critical",
        reason: "Inventory runway is not yet comfortable for a healthy growth buffer.",
        expectedEffect: "Reduce stockout risk and protect top-line continuity.",
        confidence: "High"
      }
    ],
    timeline: [
      {
        id: "timeline-1",
        title: "Product snapshot refreshed",
        description: "Latest SKU snapshot was received from backend-ready workspace payloads.",
        period: "sync",
        severity: "info",
        source: "backend"
      },
      {
        id: "timeline-2",
        title: "Recommendation plan updated",
        description: "Priority actions were refreshed for the current operating review.",
        period: "advisor",
        severity: "medium",
        source: "backend"
      }
    ],
    insight: {
      summary: "This SKU is commercially healthy enough to scale, but it still needs tighter margin discipline and safer inventory coverage.",
      topRisk: "Inventory coverage may become the limiting factor during demand spikes.",
      topOpportunity: "A healthier ad mix can unlock more profitable growth.",
      recommendation: "Stabilize inventory runway first, then reallocate spend toward higher-efficiency campaigns.",
      evidence: [
        {
          id: "evidence-1",
          label: "Inventory runway",
          detail: "Days left are below the level usually preferred for uninterrupted scaling.",
          source: "backend"
        },
        {
          id: "evidence-2",
          label: "Advertising quality",
          detail: "ROAS remains workable, but ACOS indicates room for sharper campaign control.",
          source: "backend"
        }
      ]
    },
    quickActions: [
      { id: "open-advertising", label: "Open Advertising", href: "/advertising", type: "link", enabled: true },
      { id: "open-inventory", label: "Open Inventory", href: `/inventory/${sku}`, type: "link", enabled: true },
      { id: "open-reports", label: "Open Reports", href: "/reports", type: "link", enabled: true },
      { id: "open-finance", label: "Open Finance", href: "/finance", type: "link", enabled: true },
      { id: "copy-sku", label: "Copy SKU", href: null, type: "button", enabled: false },
      { id: "open-wb-card", label: "Open WB Card", href: null, type: "button", enabled: false }
    ],
    deepLinks: buildFallbackDeepLinks(sku),
    lastUpdated: "2026-06-30T14:20:00.000Z"
  };
}

function normalizeHistory(history: ProductHistory[] | undefined): ProductHistory[] {
  if (history?.length) {
    return history;
  }

  return [
    {
      period: "today",
      revenue: null,
      profit: null,
      orders: null,
      note: "History is waiting for backend SKU snapshots."
    }
  ];
}

export function normalizeProductDetailsSnapshot(
  sku: string,
  raw: RawProductDetailsSnapshot,
  diagnostics = createFallbackDiagnostics()
): ProductDetailsSnapshot {
  return {
    overview: {
      sku: raw.overview?.sku ?? sku,
      name: raw.overview?.name ?? `Product ${sku}`,
      imageUrl: raw.overview?.imageUrl ?? null,
      category: raw.overview?.category ?? "Unassigned category",
      brand: raw.overview?.brand ?? "Unknown brand",
      vendorCode: raw.overview?.vendorCode ?? sku,
      status: raw.overview?.status ?? {
        label: "Pending",
        tone: "neutral"
      },
      health: raw.overview?.health ?? "Unknown",
      healthScore: raw.overview?.healthScore ?? null,
      abc: raw.overview?.abc ?? "n/a",
      xyz: raw.overview?.xyz ?? "n/a"
    },
    sales: {
      revenue: raw.sales?.revenue ?? null,
      orders: raw.sales?.orders ?? null,
      units: raw.sales?.units ?? null,
      averagePrice: raw.sales?.averagePrice ?? null,
      trend: raw.sales?.trend ?? "No sales trend provided."
    },
    finance: {
      profit: raw.finance?.profit ?? null,
      margin: raw.finance?.margin ?? null,
      expenses: raw.finance?.expenses ?? null,
      officialProfit: raw.finance?.officialProfit ?? null,
      difference: raw.finance?.difference ?? null
    },
    advertising: {
      spend: raw.advertising?.spend ?? null,
      roas: raw.advertising?.roas ?? null,
      acos: raw.advertising?.acos ?? null,
      campaignCount: raw.advertising?.campaignCount ?? null,
      adsHealth: raw.advertising?.adsHealth ?? "Unknown"
    },
    inventory: {
      stock: raw.inventory?.stock ?? null,
      reserved: raw.inventory?.reserved ?? null,
      available: raw.inventory?.available ?? null,
      daysLeft: raw.inventory?.daysLeft ?? null,
      forecast: raw.inventory?.forecast ?? "No inventory forecast is available.",
      warehouse: raw.inventory?.warehouse ?? "n/a"
    },
    forecast: {
      summary: raw.forecast?.summary ?? "SKU forecast payload is not available yet.",
      confidence: raw.forecast?.confidence ?? "Unknown",
      nextReorderDate: raw.forecast?.nextReorderDate ?? null
    },
    history: normalizeHistory(raw.history),
    recommendations:
      raw.recommendations?.length
        ? raw.recommendations
        : [
            {
              id: "recommendation-fallback",
              priority: "info",
              reason: "No backend SKU recommendation payload is available yet.",
              expectedEffect: "The widget remains ready for direct backend action plans.",
              confidence: "Unknown"
            }
          ],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "timeline-fallback",
              title: "Timeline pending",
              description: "No product timeline entries were returned.",
              period: "sync",
              severity: "info",
              source: "placeholder"
            }
          ],
    insight: {
      summary: raw.insight?.summary ?? "AI insight is waiting for backend-ready content.",
      topRisk: raw.insight?.topRisk ?? "No top risk provided.",
      topOpportunity: raw.insight?.topOpportunity ?? "No top opportunity provided.",
      recommendation: raw.insight?.recommendation ?? "No insight recommendation provided.",
      evidence:
        raw.insight?.evidence?.length
          ? raw.insight.evidence
          : [
              {
                id: "insight-evidence-fallback",
                label: "Placeholder",
                detail: "Frontend is ready for backend evidence payloads.",
                source: "placeholder"
              }
            ]
    },
    quickActions:
      raw.quickActions?.length
        ? raw.quickActions
        : [
            { id: "open-advertising", label: "Open Advertising", href: "/advertising", type: "link", enabled: true },
            { id: "copy-sku", label: "Copy SKU", href: null, type: "button", enabled: false }
          ],
    deepLinks: raw.deepLinks?.length ? raw.deepLinks : buildFallbackDeepLinks(sku),
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getProductDetailsMockSnapshot(sku: string) {
  return normalizeProductDetailsSnapshot(sku, createMockProductDetailsSnapshot(sku));
}

function isRawProductDetailsSnapshot(value: unknown): value is RawProductDetailsSnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    (record.overview === undefined || getObjectField(record, "overview") !== undefined) &&
    (record.sales === undefined || getObjectField(record, "sales") !== undefined) &&
    (record.finance === undefined || getObjectField(record, "finance") !== undefined) &&
    (record.advertising === undefined || getObjectField(record, "advertising") !== undefined) &&
    (record.inventory === undefined || getObjectField(record, "inventory") !== undefined) &&
    (record.forecast === undefined || getObjectField(record, "forecast") !== undefined) &&
    (record.history === undefined || Array.isArray(record.history)) &&
    (record.recommendations === undefined || Array.isArray(record.recommendations)) &&
    (record.timeline === undefined || Array.isArray(record.timeline)) &&
    (record.quickActions === undefined || Array.isArray(record.quickActions)) &&
    (record.deepLinks === undefined || Array.isArray(record.deepLinks))
  );
}

export async function fetchProductDetailsSnapshot(sku: string, signal?: AbortSignal) {
  const endpoint = `/api/products/${encodeURIComponent(sku)}`;
  const payload = await requestJson<unknown>(endpoint, { signal });
  const record = assertWorkspacePayload(payload, endpoint, "Product details");

  if (!isRawProductDetailsSnapshot(record)) {
    throw new ApiError("Product details API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: endpoint
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeProductDetailsSnapshot(
    sku,
    {
      ...record,
      history: getArrayField(record, "history"),
      recommendations: getArrayField(record, "recommendations"),
      timeline: getArrayField(record, "timeline"),
      quickActions: getArrayField(record, "quickActions"),
      deepLinks: getArrayField(record, "deepLinks"),
      insight: getObjectField(record, "insight")
        ? {
            ...(getObjectField(record, "insight") as Partial<ProductInsight>),
            evidence: getArrayField(getObjectField(record, "insight") ?? {}, "evidence")
          }
        : undefined
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
