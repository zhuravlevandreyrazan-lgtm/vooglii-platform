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
      recommendation: "Пополнить запас в течение 3 дней",
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
      recommendation: "Следить за распродажей и держать слот на пополнение",
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
      recommendation: "Сохранить текущий график поставок",
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
      reason: "Мало дней запаса при сильном прогнозе спроса.",
      expectedCoverage: "22 дня",
      warehouse: "Kazan"
    },
    {
      id: "restock-2",
      sku: "VOO-BG-018",
      recommendedQuantity: 120,
      priority: "high",
      reason: "Нужно защитить ключевой ассортимент от скачков спроса.",
      expectedCoverage: "18 дней",
      warehouse: "Elektrougli"
    }
  ],
  supplyPriority: [
    {
      id: "supply-1",
      level: "critical",
      reason: "Один быстрорастущий SKU близок к out-of-stock.",
      recommendation: "Ускорьте следующую поставку."
    },
    {
      id: "supply-2",
      level: "high",
      reason: "SKU с высокой выручкой нужен страховой запас.",
      recommendation: "Зарезервируйте емкость склада под следующую поставку."
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
      note: "Текущий срез по остаткам."
    },
    {
      period: "sevenDays",
      stock: 6710,
      coverage: 85,
      note: "Сводка по остаткам за 7 дней."
    },
    {
      period: "thirtyDays",
      stock: 7020,
      coverage: 88,
      note: "Сводка по остаткам за 30 дней."
    },
    {
      period: "ninetyDays",
      stock: 7450,
      coverage: 91,
      note: "Длинный тренд по запасам за 90 дней."
    }
  ],
  alerts: [
    {
      id: "inventory-alert-1",
      title: "Риск out-of-stock по критичному SKU",
      description: "Минимум один SKU может закончиться раньше следующего безопасного пополнения.",
      severity: "high",
      source: "backend"
    },
    {
      id: "inventory-alert-2",
      title: "Покрытие прогноза снизилось",
      description: "Высокооборачиваемые товары уже не везде обеспечены комфортным запасом.",
      severity: "medium",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "inventory-timeline-1",
      title: "Импорт остатков завершен",
      description: "Текущие складские данные загружены в рабочее пространство.",
      period: "import",
      severity: "info",
      source: "backend"
    },
    {
      id: "inventory-timeline-2",
      title: "Прогноз пополнения обновлен",
      description: "Актуализированы ориентиры по следующему циклу пополнения.",
      period: "forecast",
      severity: "low",
      source: "backend"
    },
    {
      id: "inventory-timeline-3",
      title: "План пополнения сформирован",
      description: "Появились приоритеты по SKU и складам для следующей поставки.",
      period: "restock",
      severity: "medium",
      source: "backend"
    }
  ],
  metrics: [
    {
      label: "Состояние остатков",
      value: "WATCH",
      note: "Общая оценка состояния остатков.",
      tone: "watch"
    },
    {
      label: "Покрытие прогноза",
      value: formatPercent(82, 0),
      note: "Насколько текущие запасы покрывают спрос.",
      tone: "accent"
    },
    {
      label: "Средний запас в днях",
      value: "14 дней",
      note: "Среднее количество дней до исчерпания запаса.",
      tone: "watch"
    },
    {
      label: "Складов в отчете",
      value: "3",
      note: "Сколько складов учтено в текущих данных.",
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
    forecast: "Прогноз появится после синхронизации",
    warehouse: "Нет данных",
    health: "Unknown",
    priority: "Pending",
    recommendation: "Показатели появятся после загрузки данных по складам.",
    status: {
      label: "Нет данных",
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
      inventoryHealth: localizeStatus(raw.summary?.inventoryHealth ?? "Unknown"),
      warehouseCount: raw.summary?.warehouseCount ?? null,
      lastUpdated: raw.summary?.lastUpdated ?? raw.lastUpdated ?? null
    },
    health: {
      inventoryHealth: localizeStatus(raw.health?.inventoryHealth ?? "Unknown"),
      coverage: raw.health?.coverage ?? null,
      forecastConfidence: localizeKnownText(raw.health?.forecastConfidence ?? "Unknown"),
      criticalStock: raw.health?.criticalStock ?? null,
      lowStock: raw.health?.lowStock ?? null,
      warehouseStatus: localizeKnownText(raw.health?.warehouseStatus ?? "No warehouse status available.")
    },
    items: raw.items?.length ? raw.items : [fallbackSku],
    restockPlan:
      raw.restockPlan?.length
        ? raw.restockPlan
        : [
            {
              id: "restock-fallback",
              sku: "План пополнения пока не сформирован",
              recommendedQuantity: null,
              priority: "info",
              reason: "Система пока не вернула рекомендации по пополнению.",
              expectedCoverage: "Нет данных",
              warehouse: "Нет данных"
            }
          ],
    supplyPriority:
      raw.supplyPriority?.length
        ? raw.supplyPriority
        : [
            {
              id: "supply-fallback",
              level: "low",
              reason: "Приоритет поставок появится после синхронизации.",
              recommendation: "Проверьте данные склада позже."
            }
          ],
    warehouses:
      raw.warehouses?.length
        ? raw.warehouses
        : [
            {
              id: "warehouse-fallback",
              warehouse: "Данные по складам появятся после синхронизации",
              currentStock: null,
              criticalSku: null,
              forecast: "Нет данных",
              health: "Unknown",
              status: "Нет данных"
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
              note: "История остатков появится после загрузки данных."
            }
          ],
    alerts:
      raw.alerts?.length
        ? raw.alerts
        : [
            {
              id: "inventory-alert-fallback",
              title: "Сигналы по остаткам пока не поступали",
              description: "После синхронизации здесь появятся предупреждения по остаткам.",
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
              title: "Лента остатков обновится после синхронизации",
              description: "События по складам и пополнению появятся автоматически.",
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
              label: "Метрики остатков появятся после синхронизации",
              value: "Нет данных",
              note: "Показатели будут доступны после загрузки данных.",
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
