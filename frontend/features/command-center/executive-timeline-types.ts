export type ExecutiveTimelinePeriod = "yesterday" | "today" | "tomorrow" | "week";

export type ExecutiveTimelineSeverity = "critical" | "high" | "medium" | "low" | "info";

export type ExecutiveTimelineEvent = {
  id: string;
  period: ExecutiveTimelinePeriod;
  title: string;
  description: string;
  severity: ExecutiveTimelineSeverity;
  source: "kpi" | "executiveBrief" | "priorityActions" | "fallback";
};
