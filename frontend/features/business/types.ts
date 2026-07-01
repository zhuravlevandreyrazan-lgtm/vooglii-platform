import type { StatusTone } from "@/types/platform";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type BusinessPeriodKey = "today" | "yesterday" | "sevenDays" | "thirtyDays";

export type BusinessWidget =
  | "revenue"
  | "profit"
  | "margin"
  | "orders"
  | "returns"
  | "averageOrderValue"
  | "unitsSold"
  | "health";

export type BusinessMetricState = "ready" | "unknown";

export type BusinessMetric = {
  key: BusinessWidget;
  label: string;
  value: string;
  numericValue: number;
  delta: string;
  note: string;
  tone: StatusTone;
  state: BusinessMetricState;
};

export type BusinessTrend = {
  key: BusinessPeriodKey;
  label: string;
  revenue: number;
  profit: number;
  margin: number;
  orders: number;
  returns: number;
  averageOrderValue: number;
  unitsSold: number;
};

export type BusinessProduct = {
  sku: string;
  title: string;
  revenue: number;
  profit: number;
  margin: number;
  status: string;
};

export type BusinessSnapshot = {
  summary: {
    revenue: number | null;
    profit: number | null;
    margin?: number | null;
    orders: number | null;
    returns: number | null;
    averageOrderValue?: number | null;
    unitsSold: number | null;
  };
  trends: {
    revenue: number;
    profit: number;
    margin: number;
    returns: number;
  };
  healthScore?: number;
  healthStatus?: string;
  periods: Record<BusinessPeriodKey, BusinessTrend>;
  topProducts: BusinessProduct[];
  generatedAt?: string | null;
  diagnostics?: WorkspaceDiagnostics;
};

export type BusinessKpis = {
  revenue: BusinessMetric;
  profit: BusinessMetric;
  margin: BusinessMetric;
  orders: BusinessMetric;
  returns: BusinessMetric;
  averageOrderValue: BusinessMetric;
  unitsSold: BusinessMetric;
  revenueTrend: BusinessMetric;
  profitTrend: BusinessMetric;
  marginTrend: BusinessMetric;
  healthScore: BusinessMetric;
  cards: BusinessMetric[];
};

export type BusinessInsight = {
  summary: string;
  strengths: string[];
  weaknesses: string[];
  risks: string[];
  opportunities: string[];
  confidence: "high" | "medium" | "low";
  generatedAt: string | null;
};

export type BusinessAlert = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "kpi" | "insight" | "fallback";
};
