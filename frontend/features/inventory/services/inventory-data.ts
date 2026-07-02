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
    totalStock: null,
    criticalSku: null,
    daysLeftAverage: null,
    forecastCoverage: null,
    inventoryHealth: "DEGRADED",
    warehouseCount: null,
    lastUpdated: null,
    totalSku: null,
    inStockSku: null,
    outOfStockSku: null,
    lowStockSku: null,
    overstockSku: null,
    estimatedCoverageDays: null,
    status: "Данные появятся после первой синхронизации"
  },
  health: {
    inventoryHealth: "DEGRADED",
    coverage: null,
    forecastConfidence: "Нет данных",
    criticalStock: null,
    lowStock: null,
    warehouseStatus: "Данные появятся после первой синхронизации остатков."
  },
  items: [],
  restockPlan: [],
  supplyPriority: [],
  warehouses: [],
  history: [],
  alerts: [
    {
      id: "inventory-alert-empty",
      title: "Нет складских данных",
      description: "Данные появятся после первой синхронизации остатков Wildberries.",
      severity: "info",
      source: "backend"
    }
  ],
  timeline: [],
  metrics: [
    {
      label: "Состояние остатков",
      value: "Нет данных",
      note: "Показатели появятся после загрузки продаж и складских остатков.",
      tone: "neutral"
    }
  ],
  lastUpdated: null
};

export function normalizeInventorySnapshot(
  raw: RawInventorySnapshot,
  diagnostics = createFallbackDiagnostics()
): InventorySnapshot {
  return {
    summary: {
      totalStock: raw.summary?.totalStock ?? null,
      criticalSku: raw.summary?.criticalSku ?? null,
      daysLeftAverage: raw.summary?.daysLeftAverage ?? raw.summary?.estimatedCoverageDays ?? null,
      forecastCoverage: raw.summary?.forecastCoverage ?? null,
      inventoryHealth: localizeStatus(raw.summary?.inventoryHealth ?? "Unknown"),
      warehouseCount: raw.summary?.warehouseCount ?? null,
      lastUpdated: raw.summary?.lastUpdated ?? raw.lastUpdated ?? null,
      totalSku: raw.summary?.totalSku ?? null,
      inStockSku: raw.summary?.inStockSku ?? null,
      outOfStockSku: raw.summary?.outOfStockSku ?? null,
      lowStockSku: raw.summary?.lowStockSku ?? null,
      overstockSku: raw.summary?.overstockSku ?? null,
      estimatedCoverageDays: raw.summary?.estimatedCoverageDays ?? raw.summary?.daysLeftAverage ?? null,
      status: localizeKnownText(raw.summary?.status ?? "Данные появятся после первой синхронизации")
    },
    health: {
      inventoryHealth: localizeStatus(raw.health?.inventoryHealth ?? "Unknown"),
      coverage: raw.health?.coverage ?? null,
      forecastConfidence: localizeKnownText(raw.health?.forecastConfidence ?? "Нет данных"),
      criticalStock: raw.health?.criticalStock ?? null,
      lowStock: raw.health?.lowStock ?? null,
      warehouseStatus: localizeKnownText(raw.health?.warehouseStatus ?? "Нет данных по складам")
    },
    items: raw.items ?? [],
    restockPlan: raw.restockPlan ?? [],
    supplyPriority: raw.supplyPriority ?? [],
    warehouses: raw.warehouses ?? [],
    history: raw.history ?? [],
    alerts: raw.alerts ?? [],
    timeline: raw.timeline ?? [],
    metrics: raw.metrics ?? [],
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
