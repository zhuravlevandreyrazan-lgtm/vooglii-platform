import type {
  ForecastPeriod,
  ForecastSimulation,
  ForecastSnapshot,
  ForecastWindowKey
} from "@/features/forecast/types";
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

type RawForecastResponse = {
  summary?: {
    status?: string;
    message?: string;
    confidence?: number | null;
  };
  periods?: Partial<Record<ForecastWindowKey, Partial<ForecastPeriod>>>;
  salesForecast?: Partial<ForecastSnapshot["salesForecast"]>;
  profitForecast?: Partial<ForecastSnapshot["profitForecast"]>;
  inventoryForecast?: Partial<ForecastSnapshot["inventoryForecast"]>;
  advertisingForecast?: Partial<ForecastSnapshot["advertisingForecast"]>;
  risks?: ForecastSnapshot["risks"];
  opportunities?: ForecastSnapshot["opportunities"];
  scenarios?: ForecastSnapshot["scenarios"];
  supportingProducts?: ForecastSnapshot["supportingProducts"];
  generatedAt?: string | null;
};

type ForecastSimulationRequest = {
  type: "increase_ads" | "reduce_ads" | "restock";
  sku?: string | null;
  value?: number | null;
};

function normalizePeriod(raw?: Partial<ForecastPeriod>): ForecastPeriod {
  return {
    status: raw?.status ?? "insufficient_data",
    expectedOrders: raw?.expectedOrders ?? null,
    expectedRevenue: raw?.expectedRevenue ?? null,
    expectedUnits: raw?.expectedUnits ?? null,
    trend: raw?.trend ?? "Недостаточно данных",
    confidence: raw?.confidence ?? null,
    explanation: raw?.explanation ?? "Прогноз появится после накопления истории."
  };
}

export function getForecastMockSnapshot(): ForecastSnapshot {
  return {
    summary: {
      status: "insufficient_data",
      message: "Данные появятся после первой синхронизации продаж, рекламы и остатков.",
      confidence: null
    },
    periods: {
      sevenDays: normalizePeriod(),
      fourteenDays: normalizePeriod(),
      thirtyDays: normalizePeriod()
    },
    salesForecast: {
      status: "insufficient_data",
      historyDays: null,
      activeDays: null,
      confidence: null,
      trend: "Недостаточно данных",
      explanation: "История продаж пока не накоплена."
    },
    profitForecast: {
      status: "insufficient_data",
      expectedOperatingProfit: null,
      expectedMargin: null,
      expectedProfitChange: null,
      riskOfProfitDrop: null,
      mainProfitDrivers: [],
      periods: {
        sevenDays: { expectedOperatingProfit: null, expectedMargin: null },
        fourteenDays: { expectedOperatingProfit: null, expectedMargin: null },
        thirtyDays: { expectedOperatingProfit: null, expectedMargin: null }
      },
      explanation: "Прогноз прибыли появится после загрузки финансового контура."
    },
    inventoryForecast: {
      status: "insufficient_data",
      restockNeeded: null,
      affectedRevenue: null,
      scaleAllowed: null,
      mainRisk: null,
      message: "Прогноз по остаткам появится после первой синхронизации."
    },
    advertisingForecast: {
      status: "insufficient_data",
      expectedSpend: null,
      expectedROAS: null,
      expectedACOS: null,
      overspendRisk: null,
      scalePotential: null,
      explanation: "Прогноз по рекламе появится после загрузки рекламной истории."
    },
    risks: [],
    opportunities: [],
    scenarios: [],
    supportingProducts: [],
    generatedAt: null,
    diagnostics: createFallbackDiagnostics()
  };
}

export function normalizeForecastSnapshot(
  raw: RawForecastResponse,
  diagnostics = createFallbackDiagnostics()
): ForecastSnapshot {
  const fallback = getForecastMockSnapshot();
  return {
    summary: {
      status: raw.summary?.status ?? fallback.summary.status,
      message: raw.summary?.message ?? fallback.summary.message,
      confidence: raw.summary?.confidence ?? fallback.summary.confidence
    },
    periods: {
      sevenDays: normalizePeriod(raw.periods?.sevenDays),
      fourteenDays: normalizePeriod(raw.periods?.fourteenDays),
      thirtyDays: normalizePeriod(raw.periods?.thirtyDays)
    },
    salesForecast: {
      ...fallback.salesForecast,
      ...raw.salesForecast
    },
    profitForecast: {
      ...fallback.profitForecast,
      ...raw.profitForecast,
      periods: {
        sevenDays: raw.profitForecast?.periods?.sevenDays ?? fallback.profitForecast.periods.sevenDays,
        fourteenDays: raw.profitForecast?.periods?.fourteenDays ?? fallback.profitForecast.periods.fourteenDays,
        thirtyDays: raw.profitForecast?.periods?.thirtyDays ?? fallback.profitForecast.periods.thirtyDays
      }
    },
    inventoryForecast: {
      ...fallback.inventoryForecast,
      ...raw.inventoryForecast
    },
    advertisingForecast: {
      ...fallback.advertisingForecast,
      ...raw.advertisingForecast
    },
    risks: raw.risks ?? [],
    opportunities: raw.opportunities ?? [],
    scenarios: raw.scenarios ?? [],
    supportingProducts: raw.supportingProducts ?? [],
    generatedAt: raw.generatedAt ?? null,
    diagnostics
  };
}

function isRawForecastResponse(value: unknown): value is RawForecastResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    (record.summary === undefined || getObjectField(record, "summary") !== undefined) &&
    (record.periods === undefined || getObjectField(record, "periods") !== undefined) &&
    (record.risks === undefined || Array.isArray(record.risks)) &&
    (record.opportunities === undefined || Array.isArray(record.opportunities)) &&
    (record.scenarios === undefined || Array.isArray(record.scenarios))
  );
}

function normalizeEffectMap(
  value: Record<string, unknown> | undefined
): Record<string, string | number | null> {
  if (!value) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).map(([key, entryValue]) => [
      key,
      typeof entryValue === "number" || typeof entryValue === "string" || entryValue === null
        ? entryValue
        : String(entryValue)
    ])
  );
}

export async function fetchForecastSnapshot(signal?: AbortSignal): Promise<ForecastSnapshot> {
  const payload = await requestJson<unknown>(apiEndpoints.forecast, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.forecast, "Forecast");

  if (!isRawForecastResponse(record)) {
    throw new ApiError("Forecast API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.forecast
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeForecastSnapshot(
    {
      ...record,
      risks: getArrayField(record, "risks"),
      opportunities: getArrayField(record, "opportunities"),
      scenarios: getArrayField(record, "scenarios"),
      supportingProducts: getArrayField(record, "supportingProducts")
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}

export async function simulateForecast(
  request: ForecastSimulationRequest,
  signal?: AbortSignal
): Promise<ForecastSimulation> {
  const payload = await requestJson<unknown>(apiEndpoints.forecastSimulate, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request)
  });
  const record = assertWorkspacePayload(payload, apiEndpoints.forecastSimulate, "Forecast simulate");

  return {
    status: typeof record.status === "string" ? record.status : "insufficient_data",
    recommendation: typeof record.recommendation === "string" ? record.recommendation : "Недостаточно данных для моделирования.",
    confidence: typeof record.confidence === "number" ? record.confidence : null,
    expectedEffect: normalizeEffectMap(getObjectField(record, "expectedEffect")),
    risks: getArrayField<string>(record, "risks")
  };
}
