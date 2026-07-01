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
    { id: "advertising", label: "Реклама", href: "/advertising", description: `Контекст рекламных кампаний для ${sku}.` },
    { id: "inventory", label: "Остатки", href: `/inventory/${sku}`, description: `Детализация остатков для ${sku}.` },
    { id: "finance", label: "Финансы", href: "/finance", description: `Финансовый контекст и прибыльность для ${sku}.` },
    { id: "advisor", label: "ИИ-советник", href: "/advisor", description: `Рекомендации советника по ${sku}.` },
    { id: "reports", label: "Отчеты", href: "/reports", description: `Выгрузки и отчеты по ${sku}.` },
    { id: "executive", label: "Главная", href: "/executive", description: "Общая управленческая сводка и контекст руководителя." },
    { id: "business", label: "Бизнес", href: "/business", description: "Бизнес-показатели для этой товарной группы." }
  ];
}

function createMockProductDetailsSnapshot(sku: string): RawProductDetailsSnapshot {
  return {
    overview: {
      sku,
      name: `Товар ${sku}`,
      imageUrl: null,
      category: "Ассортимент маркетплейса",
      brand: "VOOGLII",
      vendorCode: `${sku}-VC`,
      status: {
        label: "Рабочий обзор",
        tone: "accent"
      },
      health: "Требует внимания",
      healthScore: 72,
      abc: "A",
      xyz: "Y"
    },
    sales: {
      revenue: 69480,
      orders: 312,
      units: 338,
      averagePrice: 206,
      trend: "Спрос остается стабильным с точками роста."
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
      adsHealth: "Требует внимания"
    },
    inventory: {
      stock: 186,
      reserved: 19,
      available: 167,
      daysLeft: 11,
      forecast: "Спрос остается стабильным до следующего окна пополнения.",
      warehouse: "Электроугли"
    },
    forecast: {
      summary: "Прогноз пока представлен как краткая backend-сводка без фронтенд-расчетов.",
      confidence: "Средняя",
      nextReorderDate: null
    },
    history: [
      {
        period: "today",
        revenue: 21480,
        profit: 6410,
        orders: 42,
        note: "Показатели за текущий день."
      },
      {
        period: "sevenDays",
        revenue: 148300,
        profit: 42110,
        orders: 211,
        note: "Сводка за последние 7 дней."
      },
      {
        period: "thirtyDays",
        revenue: 411800,
        profit: 122430,
        orders: 612,
        note: "История по товару за 30 дней."
      },
      {
        period: "ninetyDays",
        revenue: 1094700,
        profit: 312700,
        orders: 1714,
        note: "История за 90 дней для будущего расширения графиков."
      }
    ],
    recommendations: [
      {
        id: "rec-1",
        priority: "high",
        reason: "Маржинальность находится под давлением на фоне смешанной эффективности рекламы.",
        expectedEffect: "Поможет восстановить вклад в прибыль перед следующим этапом роста.",
        confidence: "Средняя"
      },
      {
        id: "rec-2",
        priority: "critical",
        reason: "Запаса товара пока недостаточно для безопасного роста.",
        expectedEffect: "Снизит риск out-of-stock и защитит выручку.",
        confidence: "Высокая"
      }
    ],
    timeline: [
      {
        id: "timeline-1",
        title: "Карточка товара обновлена",
        description: "Последний SKU-снимок получен из рабочего backend-потока.",
        period: "sync",
        severity: "info",
        source: "backend"
      },
      {
        id: "timeline-2",
        title: "План рекомендаций обновлен",
        description: "Приоритетные действия были пересчитаны для текущего обзора.",
        period: "advisor",
        severity: "medium",
        source: "backend"
      }
    ],
    insight: {
      summary: "SKU выглядит достаточно здоровым для роста, но ему все еще нужна лучшая дисциплина по марже и более безопасный запас остатков.",
      topRisk: "Остатки могут стать главным ограничением при всплеске спроса.",
      topOpportunity: "Более качественная рекламная структура может дать более прибыльный рост.",
      recommendation: "Сначала стабилизируйте запас, затем перераспределите рекламный бюджет в более эффективные кампании.",
      evidence: [
        {
          id: "evidence-1",
          label: "Запас остатков",
          detail: "Количество дней запаса ниже уровня, который обычно считается комфортным для роста.",
          source: "backend"
        },
        {
          id: "evidence-2",
          label: "Качество рекламы",
          detail: "ROAS остается рабочим, но ACOS показывает пространство для более точного управления кампаниями.",
          source: "backend"
        }
      ]
    },
    quickActions: [
      { id: "open-advertising", label: "Открыть рекламу", href: "/advertising", type: "link", enabled: true },
      { id: "open-inventory", label: "Открыть остатки", href: `/inventory/${sku}`, type: "link", enabled: true },
      { id: "open-reports", label: "Открыть отчеты", href: "/reports", type: "link", enabled: true },
      { id: "open-finance", label: "Открыть финансы", href: "/finance", type: "link", enabled: true },
      { id: "copy-sku", label: "Скопировать SKU", href: null, type: "button", enabled: false },
      { id: "open-wb-card", label: "Открыть карточку WB", href: null, type: "button", enabled: false }
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
      note: "История появится после загрузки SKU-данных."
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
      name: raw.overview?.name ?? `Товар ${sku}`,
      imageUrl: raw.overview?.imageUrl ?? null,
      category: raw.overview?.category ?? "Категория не указана",
      brand: raw.overview?.brand ?? "Бренд не указан",
      vendorCode: raw.overview?.vendorCode ?? sku,
      status: raw.overview?.status ?? {
        label: "Ожидает данные",
        tone: "neutral"
      },
      health: raw.overview?.health ?? "Нет данных",
      healthScore: raw.overview?.healthScore ?? null,
      abc: raw.overview?.abc ?? "n/a",
      xyz: raw.overview?.xyz ?? "n/a"
    },
    sales: {
      revenue: raw.sales?.revenue ?? null,
      orders: raw.sales?.orders ?? null,
      units: raw.sales?.units ?? null,
      averagePrice: raw.sales?.averagePrice ?? null,
      trend: raw.sales?.trend ?? "Динамика продаж пока не предоставлена."
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
      adsHealth: raw.advertising?.adsHealth ?? "Нет данных"
    },
    inventory: {
      stock: raw.inventory?.stock ?? null,
      reserved: raw.inventory?.reserved ?? null,
      available: raw.inventory?.available ?? null,
      daysLeft: raw.inventory?.daysLeft ?? null,
      forecast: raw.inventory?.forecast ?? "Прогноз по остаткам пока недоступен.",
      warehouse: raw.inventory?.warehouse ?? "нет данных"
    },
    forecast: {
      summary: raw.forecast?.summary ?? "Прогноз по SKU пока не получен.",
      confidence: raw.forecast?.confidence ?? "Нет данных",
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
              reason: "Backend пока не вернул рекомендации по SKU.",
              expectedEffect: "Виджет готов к подключению прямых backend-планов действий.",
              confidence: "Нет данных"
            }
          ],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "timeline-fallback",
              title: "История событий пока недоступна",
              description: "По товару пока нет событийной ленты.",
              period: "sync",
              severity: "info",
              source: "placeholder"
            }
          ],
    insight: {
      summary: raw.insight?.summary ?? "Инсайт появится после загрузки backend-аналитики.",
      topRisk: raw.insight?.topRisk ?? "Главный риск пока не определен.",
      topOpportunity: raw.insight?.topOpportunity ?? "Точка роста пока не определена.",
      recommendation: raw.insight?.recommendation ?? "Рекомендация пока не сформирована.",
      evidence:
        raw.insight?.evidence?.length
          ? raw.insight.evidence
          : [
              {
                id: "insight-evidence-fallback",
                label: "Ожидание данных",
                detail: "Фронтенд готов к приему доказательной базы с backend.",
                source: "placeholder"
              }
            ]
    },
    quickActions:
      raw.quickActions?.length
        ? raw.quickActions
        : [
            { id: "open-advertising", label: "Открыть рекламу", href: "/advertising", type: "link", enabled: true },
            { id: "copy-sku", label: "Скопировать SKU", href: null, type: "button", enabled: false }
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
  const record = assertWorkspacePayload(payload, endpoint, "Карточка товара");

  if (!isRawProductDetailsSnapshot(record)) {
    throw new ApiError("Ответ API по карточке товара имеет некорректный формат.", {
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
