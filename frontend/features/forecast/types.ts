import type { WorkspaceDiagnostics } from "@/shared/api";

export type ForecastWindowKey = "sevenDays" | "fourteenDays" | "thirtyDays";

export type ForecastPeriod = {
  status: string;
  expectedOrders: number | null;
  expectedRevenue: number | null;
  expectedUnits: number | null;
  trend: string;
  confidence: number | null;
  explanation: string;
};

export type ForecastRisk = {
  id: string;
  title: string;
  description: string;
  level: string;
  action?: string | null;
  confidence?: number | null;
};

export type ForecastScenario = {
  id: string;
  title: string;
  revenue: number | null;
  profit: number | null;
  riskLevel: string;
  actions: string[];
};

export type ForecastSimulation = {
  status: string;
  recommendation: string;
  confidence: number | null;
  expectedEffect: Record<string, number | string | null>;
  risks: string[];
};

export type ForecastSnapshot = {
  summary: {
    status: string;
    message: string;
    confidence: number | null;
  };
  periods: Record<ForecastWindowKey, ForecastPeriod>;
  salesForecast: {
    status: string;
    historyDays: number | null;
    activeDays: number | null;
    confidence: number | null;
    trend: string;
    explanation: string;
  };
  profitForecast: {
    status: string;
    expectedOperatingProfit: number | null;
    expectedMargin: number | null;
    expectedProfitChange: number | null;
    riskOfProfitDrop: boolean | null;
    mainProfitDrivers: string[];
    periods: Record<ForecastWindowKey, { expectedOperatingProfit: number | null; expectedMargin: number | null }>;
    explanation: string;
    confidence?: number | null;
  };
  inventoryForecast: {
    status: string;
    restockNeeded: boolean | null;
    affectedRevenue: number | null;
    scaleAllowed: boolean | null;
    mainRisk?: { title?: string | null; description?: string | null } | null;
    message: string;
  };
  advertisingForecast: {
    status: string;
    expectedSpend: number | null;
    expectedROAS: number | null;
    expectedACOS: number | null;
    overspendRisk: boolean | null;
    scalePotential: boolean | null;
    explanation: string;
    confidence?: number | null;
  };
  risks: ForecastRisk[];
  opportunities: ForecastRisk[];
  scenarios: ForecastScenario[];
  supportingProducts: Array<Record<string, unknown>>;
  generatedAt: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
