export type WorkspaceKey =
  | "command-center"
  | "business"
  | "finance"
  | "products"
  | "advertising"
  | "analytics"
  | "ai"
  | "system"
  | "settings";

export type StatusTone = "healthy" | "watch" | "risk" | "neutral" | "accent";

export type CommandCenterDataSource = "real" | "mock_fallback" | "demo";
export type CommandCenterRuntimeSource = "live" | "cache" | "stale_cache" | "degraded" | "fallback" | "demo" | "dev";

export type NavItem = {
  label: string;
  href: string;
  key: WorkspaceKey;
  description: string;
};

export type NotificationItem = {
  id: string;
  title: string;
  description: string;
  tone: StatusTone;
};

export type HealthMetric = {
  label: string;
  value: string;
  delta: string;
  tone: StatusTone;
  note: string;
};

export type TimelineEvent = {
  id: string;
  time: string;
  title: string;
  detail: string;
  tone: StatusTone;
};

export type ActionItem = {
  id: string;
  title: string;
  owner: string;
  eta: string;
  tone: StatusTone;
};

export type AlertItem = {
  id: string;
  title: string;
  detail: string;
  tone: StatusTone;
};

export type InsightItem = {
  id: string;
  eyebrow: string;
  title: string;
  summary: string;
  confidence: string;
  sources: string[];
  tone: StatusTone;
};

export type WorkspaceCard = {
  title: string;
  href: string;
  summary: string;
  status: string;
};

export type CommandCenterSnapshot = {
  businessHealth: {
    score?: number | null;
    status: string;
    summary: string;
  };
  executiveBrief: InsightItem;
  kpis: HealthMetric[];
  timeline: TimelineEvent[];
  actions: ActionItem[];
  alerts: AlertItem[];
  workspaces: WorkspaceCard[];
  notifications: NotificationItem[];
};

export type CommandCenterScreenData = {
  snapshot: CommandCenterSnapshot;
  source: CommandCenterDataSource;
  runtimeSource?: CommandCenterRuntimeSource;
  apiBaseUrl: string;
  fallbackReason?: string;
};
