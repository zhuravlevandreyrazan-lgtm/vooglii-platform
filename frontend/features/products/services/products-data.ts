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
      recommendation: "Увеличьте запас перед следующим промо-периодом.",
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
      recommendation: "Снизьте неэффективный трафик и защитите маржу перед масштабированием.",
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
        forecast: "Demand accelerating",
        riskLevel: "High"
      },
      status: {
        label: "Restock needed",
        tone: "risk"
      },
      recommendation: "Приоритизируйте пополнение и проверяйте спрос ежедневно.",
      trend: "Fast growth",
      warehouse: "Kazan"
    }
  ],
  recommendations: [
    {
      id: "product-rec-1",
      sku: "VOO-HM-203",
      recommendation: "Пополнить запас в течение 3 дней",
      reason: "Остаток быстро сокращается при сильном спросе.",
      priority: "critical",
      confidence: "High",
      expectedEffect: "Поможет избежать out-of-stock и сохранить выручку."
    },
    {
      id: "product-rec-2",
      sku: "VOO-BG-018",
      recommendation: "Проверить эффективность платного трафика",
      reason: "Маржа и ACOS указывают на слабое качество рекламы.",
      priority: "high",
      confidence: "Medium",
      expectedEffect: "Поможет вернуть маржу на SKU с хорошим объемом продаж."
    }
  ],
  history: [
    {
      period: "today",
      sales: 21480,
      advertising: 4210,
      note: "Продажи и реклама за сегодня."
    },
    {
      period: "sevenDays",
      sales: 148300,
      advertising: 23640,
      note: "Сводка по товарам за 7 дней."
    },
    {
      period: "thirtyDays",
      sales: 411800,
      advertising: 68420,
      note: "Сводка по товарам за 30 дней."
    },
    {
      period: "ninetyDays",
      sales: 1094700,
      advertising: 183600,
      note: "Длинный тренд по товарам за 90 дней."
    }
  ],
  inventoryPreview: [],
  alerts: [
    {
      id: "product-alert-1",
      title: "Риск потери продаж по растущему SKU",
      description: "Минимум у одного SKU мало дней запаса при стабильном спросе.",
      severity: "high",
      source: "backend"
    },
    {
      id: "product-alert-2",
      title: "Давление на маржу в ключевом ассортименте",
      description: "Один из товаров с высокой выручкой показывает слабую прибыльность.",
      severity: "medium",
      source: "backend"
    }
  ],
  timeline: [
    {
      id: "product-timeline-1",
      title: "Синхронизация товаров завершена",
      description: "Товарная аналитика обновлена и доступна в рабочем пространстве.",
      period: "sync",
      severity: "info",
      source: "backend"
    },
    {
      id: "product-timeline-2",
      title: "План действий по SKU обновлен",
      description: "Актуализированы сигналы по товарам и рекомендации по ассортименту.",
      period: "audit",
      severity: "medium",
      source: "backend"
    },
    {
      id: "product-timeline-3",
      title: "Прогноз по товарам обновлен",
      description: "Добавлены свежие ориентиры для планирования ассортимента.",
      period: "forecast",
      severity: "low",
      source: "backend"
    }
  ],
  actions: [
    {
      id: "product-action-1",
      sku: "VOO-HM-203",
      action: "Срочно пополнить",
      status: "Open"
    }
  ],
  lastUpdated: "2026-06-30T13:30:00.000Z"
};

function emptyProductCard(): ProductCard {
  return {
    sku: "SKU-PENDING",
    name: "Данные по товарам появятся после синхронизации",
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
      status: "Нет данных",
      abc: "n/a",
      xyz: "n/a",
      forecast: "Прогноз появится после синхронизации",
      riskLevel: "Unknown"
    },
    status: {
      label: "Нет данных",
      tone: "neutral"
    },
    recommendation: "Показатели появятся после загрузки данных кабинета.",
    trend: "Нет данных",
    warehouse: "Нет данных"
  };
}

export function normalizeProductSnapshot(
  raw: RawProductSnapshot,
  diagnostics = createFallbackDiagnostics()
): ProductSnapshot {
  return {
    summary: {
      skuCount: raw.summary?.skuCount ?? 0,
      activeSku: raw.summary?.activeSku ?? 0,
      problemSku: raw.summary?.problemSku ?? 0,
      riskSku: raw.summary?.riskSku ?? 0,
      growthSku: raw.summary?.growthSku ?? 0,
      lastUpdated: raw.summary?.lastUpdated ?? raw.lastUpdated ?? null
    },
    products: raw.products ?? [],
    recommendations: raw.recommendations ?? [],
    history: raw.history ?? [],
    inventoryPreview: raw.inventoryPreview ?? [],
    alerts: raw.alerts ?? [],
    timeline: raw.timeline ?? [],
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
