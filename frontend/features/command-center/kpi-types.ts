import type { HealthMetric, StatusTone } from "@/types/platform";

export type KpiMetricKey =
  | "revenue"
  | "profit"
  | "margin"
  | "orders"
  | "advertisingSpend"
  | "roas"
  | "acos"
  | "businessHealth";

export type KpiMetricState = "ready" | "unknown" | "empty";

export type KpiTrendDirection = "up" | "down" | "flat" | "unknown";

export type KpiTrend = {
  value: string;
  direction: KpiTrendDirection;
  summary: string;
};

export type KpiMetric = {
  key: KpiMetricKey;
  label: string;
  value: string;
  numericValue: number;
  unit: "currency" | "percent" | "count" | "ratio" | "score";
  state: KpiMetricState;
  tone: StatusTone;
  note: string;
  trend: KpiTrend;
  source: string;
};

export type KpiRisk = {
  title: string;
  summary: string;
  tone: StatusTone;
  source: string;
};

export type KpiOpportunity = {
  title: string;
  summary: string;
  tone: StatusTone;
  source: string;
};

export type CommandCenterKpis = {
  revenue: KpiMetric;
  profit: KpiMetric;
  margin: KpiMetric;
  orders: KpiMetric;
  advertisingSpend: KpiMetric;
  roas: KpiMetric;
  acos: KpiMetric;
  businessHealth: KpiMetric;
  topRisk: KpiRisk | null;
  topOpportunity: KpiOpportunity | null;
  cards: HealthMetric[];
};
