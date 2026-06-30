import type { StatusTone } from "@/types/platform";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type FinanceWidget =
  | "operatingProfit"
  | "officialProfit"
  | "profitDifference"
  | "financeHealth"
  | "trustScore"
  | "coverage"
  | "confidence"
  | "residualModel"
  | "income"
  | "expenses";

export type FinanceMetric = {
  key: FinanceWidget;
  label: string;
  value: string;
  note: string;
  tone: StatusTone;
};

export type FinanceSummary = {
  operatingProfit: number | null;
  officialProfit: number | null;
  difference: number | null;
  health: string;
  trustScore: number | null;
  status: string;
};

export type FinanceQuality = {
  coverage: number | null;
  residualUsage: string;
  trustScore: number | null;
  confidence: string;
  health: string;
};

export type FinanceDifference = {
  operatingProfit: number | null;
  officialProfit: number | null;
  difference: number | null;
  differencePercent: number | null;
  reason: string;
  explanation?: string | null;
};

export type FinanceAlert = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type FinanceTimelineEvent = {
  id: string;
  title: string;
  description: string;
  period: "latest" | "audit" | "sync";
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type FinanceSnapshot = {
  summary: FinanceSummary;
  quality: FinanceQuality;
  difference: FinanceDifference;
  metrics: FinanceMetric[];
  alerts: FinanceAlert[];
  timeline: FinanceTimelineEvent[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
