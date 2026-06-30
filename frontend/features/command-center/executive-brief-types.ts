import type { StatusTone } from "@/types/platform";

export type ExecutiveStatus =
  | "Business Stable"
  | "Attention Required"
  | "Data Pending";

export type ExecutivePriority = "high" | "medium" | "low";

export type ExecutiveConfidence = "high" | "medium" | "low";

export type ExecutiveInsight = {
  title: string;
  summary: string;
  tone: StatusTone;
  source: string;
};

export type ExecutiveRecommendation = {
  title: string;
  detail: string;
  priority: ExecutivePriority;
};

export type ExecutiveBrief = {
  greeting: string;
  overallStatus: ExecutiveStatus;
  summary: string;
  topRisk: ExecutiveInsight | null;
  topOpportunity: ExecutiveInsight | null;
  recommendation: ExecutiveRecommendation;
  confidence: ExecutiveConfidence;
  generatedAt: string | null;
};
