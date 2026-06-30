export type PriorityActionType = "ads" | "inventory" | "profit" | "risk" | "growth" | "data";

export type PriorityActionSeverity = "critical" | "high" | "medium" | "low";

export type PriorityActionImpact = "revenue" | "profit" | "efficiency" | "stability" | "visibility";

export type PriorityActionStatus = "new" | "review" | "ready";

export type PriorityAction = {
  id: string;
  type: PriorityActionType;
  severity: PriorityActionSeverity;
  title: string;
  description: string;
  impact?: PriorityActionImpact;
  recommendation: string;
  status: PriorityActionStatus;
  source: "kpi" | "executiveBrief" | "fallback";
};
