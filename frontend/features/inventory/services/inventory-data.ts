import { formatPercent } from "@/features/command-center/formatters";
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
  InventoryAlert,
  InventoryHistory,
  InventoryMetrics,
  InventoryPriority,
  InventoryRestockPlan,
  InventorySku,
  InventorySnapshot,
  InventoryTimeline,
  InventoryWarehouse
} from "@/features/inventory/types";

type RawInventorySnapshot = {
  summary?: Partial<InventorySnapshot["summary"]>;
  health?: Partial<InventorySnapshot["health"]>;
  items?: InventorySku[];
  restockPlan?: InventoryRestockPlan[];
  supplyPriority?: InventoryPriority[];
  warehouses?: InventoryWarehouse[];
  history?: InventoryHistory[];
  alerts?: InventoryAlert[];
  timeline?: InventoryTimeline[];
  metrics?: InventoryMetrics[];
  lastUpdated?: string | null;
};

const rawInventorySnapshot: RawInventorySnapshot = {
  summary: {
    totalStock: 6520,
    criticalSku: 5,
    daysLeftAverage: 14,
    forecastCoverage: 82,
    inventoryHealth: "WATCH",
    warehouseCount: 3,
    lastUpdated: "2026-06-30T14:00:00.000Z"
  },
  health: {
    inventoryHealth: "WATCH",
    coverage: 82,
    forecastConfidence: "Medium",
    criticalStock: 5,
    lowStock: 11,
    warehouseStatus: "Two warehouses stable, one under pressure"
  },
  items: [
    {
      sku: "VOO-HM-203",
      stock: 54,
      reserved: 8,
      available: 46,
      daysLeft: 5,
      forecast: "Demand accelerating",
      warehouse: "Kazan",
      health: "Risk",
      priority: "Critical",
      recommendation: "Restock within 3 days",
      status: {
        label: "Restock needed",
        tone: "risk"
      }
    },
    {
      sku: "VOO-BG-018",
      stock: 186,
      reserved: 19,
      available: 167,
      daysLeft: 11,
      forecast: "Stable demand",
      warehouse: "Elektrougli",
      health: "Watch",
      priority: "High",
      recommendation: "Monitor sell-through and hold replenishment slot",
      status: {
        label: "Monitor",
        tone: "watch"
      }
    },
    {
      sku: "VOO-TS-001",
      stock: 412,
      reserved: 36,
      available: 376,
      daysLeft: 23,
      forecast: "Stable coverage",
      warehouse: "Kolедino",
      health: "Strong",
      priority: "Low",
      recommendation: "Maintain current supply schedule",
      status: {
        label: "Stable",
        tone: "healthy"
      }
    }
  ],
  restockPlan: [
    {
      id: "restock-1",
      sku: "VOO-HM-203",
      recommendedQuantity: 240,
      priority: "critical",
      reason: "Low days left with strong forecast demand.",
      expectedCoverage: "22 days",
      warehouse: "Kazan"
    },
    {
      id: "restock-2",
      sku: "VOO-BG-018",
      recommendedQuantity: 120,
      priority: "high",
      reason: "Protect key assortment from demand spikes.",
      expectedCoverage: "18 days",
      warehouse: "Elektrougli"
    }
  ],
  supplyPriority: [
    {
      id: "supply-1",
      level: "critical",
      reason: "One fast-growing SKU is close to stockout.",
      recommendation: "Escalate the next replenishment batch."
    },
    {
      id: "supply-2",
      level: "high",
      reason: "A core revenue SKU needs a reserve buffer.",
      recommendation: "Reserve warehouse capacity for the next inbound."
    }
  ],
  warehouses: [
    {
      id: "warehouse-1",
      warehouse: "Kazan",
      currentStock: 1280,
      criticalSku: 2,
      forecast: "Demand rising",
      health: "Watch",
      status: "Pressure on fast movers"
    },
    {
      id: "warehouse-2",
      warehouse: "Elektrougli",
      currentStock: 2410,
      criticalSku: 1,
      forecast: "Stable",
      health: "Stable",
      status: "Balanced coverage"
    },
    {
      id: "warehouse-3",
      warehouse: "Kolедino",
      currentStock: 2830,
      criticalSku: 2,
      forecast: "Stable",
      health: "Strong",
      status: "Healthy stock pool"
    }
  ],
  history: [
    {
      period: "today",
      stock: 6520,
      coverage: 82,
      note: "Current inventory snapshot."
    },
    {
      period: "sevenDays",
      stock: 6710,
      coverage: 85,
      note: "Seven-day inventory and coverage summary."
    },
    {
      period: "thirtyDays",
      stock: 7020,
      coverage: 88,
      note: "Thirty-day inventory rollup."
    },
    {
      period: "ninetyDays",
      stock: 7450,
      coverage: 91,
      note: "Ninety-day inventory history snapshot."
    }
  ],
  alerts: [
    {
      id: "inventory-alert-1",
      title: "Out-of-stock risk on critical SKU",
      description: "At least one SKU is likely to run out before the next safe restock window.",
      severity: "high",
      source: "backend"
    },
    {
      id: "inventory-alert-2",
      title: "Forecast coverage weakened",
      description: "Coverage remains usable, but not all high-volume items have comfortable runway.",
      severity: "medium",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "inventory-timeline-1",
      title: "Latest inventory import completed",
      description: "Warehouse stock snapshot has been refreshed from backend-ready analytics.",
      period: "import",
      severity: "info",
      source: "backend"
    },
    {
      id: "inventory-timeline-2",
      title: "Latest forecast refreshed",
      description: "Forecast values were updated for current replenishment planning.",
      period: "forecast",
      severity: "low",
      source: "backend"
    },
    {
      id: "inventory-timeline-3",
      title: "Latest restock plan generated",
      description: "Backend restock plan is available for operational review.",
      period: "restock",
      severity: "medium",
      source: "backend"
    }
  ],
  metrics: [
    {
      label: "Inventory Health",
      value: "WATCH",
      note: "Overall inventory health from backend-ready analytics.",
      tone: "watch"
    },
    {
      label: "Forecast Coverage",
      value: formatPercent(82, 0),
      note: "Coverage percentage supplied by backend analytics.",
      tone: "accent"
    },
    {
      label: "Days Left Average",
      value: "14 days",
      note: "Average days-left measure from backend snapshot.",
      tone: "watch"
    },
    {
      label: "Warehouse Count",
      value: "3",
      note: "Warehouses currently represented in this snapshot.",
      tone: "neutral"
    }
  ],
  lastUpdated: "2026-06-30T14:00:00.000Z"
};

function emptyInventorySku(): InventorySku {
  return {
    sku: "SKU-PENDING",
    stock: null,
    reserved: null,
    available: null,
    daysLeft: null,
    forecast: "No forecast yet",
    warehouse: "n/a",
    health: "Unknown",
    priority: "Pending",
    recommendation: "Placeholder row keeps the inventory UI ready for direct backend integration.",
    status: {
      label: "Pending",
      tone: "neutral"
    }
  };
}

export function normalizeInventorySnapshot(
  raw: RawInventorySnapshot,
  diagnostics = createFallbackDiagnostics()
): InventorySnapshot {
  const fallbackSku = emptyInventorySku();

  return {
    summary: {
      totalStock: raw.summary?.totalStock ?? null,
      criticalSku: raw.summary?.criticalSku ?? null,
      daysLeftAverage: raw.summary?.daysLeftAverage ?? null,
      forecastCoverage: raw.summary?.forecastCoverage ?? null,
      inventoryHealth: raw.summary?.inventoryHealth ?? "Unknown",
      warehouseCount: raw.summary?.warehouseCount ?? null,
      lastUpdated: raw.summary?.lastUpdated ?? raw.lastUpdated ?? null
    },
    health: {
      inventoryHealth: raw.health?.inventoryHealth ?? "Unknown",
      coverage: raw.health?.coverage ?? null,
      forecastConfidence: raw.health?.forecastConfidence ?? "Unknown",
      criticalStock: raw.health?.criticalStock ?? null,
      lowStock: raw.health?.lowStock ?? null,
      warehouseStatus: raw.health?.warehouseStatus ?? "No warehouse status available."
    },
    items: raw.items?.length ? raw.items : [fallbackSku],
    restockPlan:
      raw.restockPlan?.length
        ? raw.restockPlan
        : [
            {
              id: "restock-fallback",
              sku: "No restock plan yet",
              recommendedQuantity: null,
              priority: "info",
              reason: "No backend restock plan was returned in the current snapshot.",
              expectedCoverage: "n/a",
              warehouse: "n/a"
            }
          ],
    supplyPriority:
      raw.supplyPriority?.length
        ? raw.supplyPriority
        : [
            {
              id: "supply-fallback",
              level: "low",
              reason: "No supply priority payload is available yet.",
              recommendation: "Keep placeholder architecture ready for future backend priority data."
            }
          ],
    warehouses:
      raw.warehouses?.length
        ? raw.warehouses
        : [
            {
              id: "warehouse-fallback",
              warehouse: "Warehouse data pending",
              currentStock: null,
              criticalSku: null,
              forecast: "n/a",
              health: "Unknown",
              status: "Pending backend data"
            }
          ],
    history:
      raw.history?.length
        ? raw.history
        : [
            {
              period: "today",
              stock: null,
              coverage: null,
              note: "Historical inventory data is not available yet."
            }
          ],
    alerts:
      raw.alerts?.length
        ? raw.alerts
        : [
            {
              id: "inventory-alert-fallback",
              title: "No inventory alerts available",
              description: "Backend did not return inventory alerts for the current snapshot.",
              severity: "info",
              source: "placeholder"
            }
          ],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "inventory-timeline-fallback",
              title: "Inventory timeline is waiting for backend events",
              description: "No inventory timeline entries are available yet.",
              period: "sync",
              severity: "info",
              source: "placeholder"
            }
          ],
    metrics:
      raw.metrics?.length
        ? raw.metrics
        : [
            {
              label: "Inventory metrics pending",
              value: "n/a",
              note: "No backend inventory metrics are available yet.",
              tone: "neutral"
            }
          ],
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getInventoryMockSnapshot() {
  return normalizeInventorySnapshot(rawInventorySnapshot);
}

function isRawInventorySnapshot(value: unknown): value is RawInventorySnapshot {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    (record.summary === undefined || getObjectField(record, "summary") !== undefined) &&
    (record.health === undefined || getObjectField(record, "health") !== undefined) &&
    (record.items === undefined || Array.isArray(record.items)) &&
    (record.restockPlan === undefined || Array.isArray(record.restockPlan)) &&
    (record.supplyPriority === undefined || Array.isArray(record.supplyPriority)) &&
    (record.warehouses === undefined || Array.isArray(record.warehouses)) &&
    (record.history === undefined || Array.isArray(record.history)) &&
    (record.alerts === undefined || Array.isArray(record.alerts)) &&
    (record.timeline === undefined || Array.isArray(record.timeline)) &&
    (record.metrics === undefined || Array.isArray(record.metrics))
  );
}

export async function fetchInventorySnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.inventory, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.inventory, "Inventory");

  if (!isRawInventorySnapshot(record)) {
    throw new ApiError("Inventory API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.inventory
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeInventorySnapshot(
    {
      ...record,
      items: getArrayField(record, "items"),
      restockPlan: getArrayField(record, "restockPlan"),
      supplyPriority: getArrayField(record, "supplyPriority"),
      warehouses: getArrayField(record, "warehouses"),
      history: getArrayField(record, "history"),
      alerts: getArrayField(record, "alerts"),
      timeline: getArrayField(record, "timeline"),
      metrics: getArrayField(record, "metrics")
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
