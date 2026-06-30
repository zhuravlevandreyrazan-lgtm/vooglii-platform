import type { StatusTone } from "@/types/platform";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type AdvertisingSummary = {
  advertisingSpend: number | null;
  linkedSpend: number | null;
  unlinkedSpend: number | null;
  roas: number | null;
  acos: number | null;
  adsHealth: string;
  trust: string;
  status: string;
  trend?: Array<{
    label: string;
    value: number;
  }>;
};

export type AdvertisingHealth = {
  adsHealth: string;
  linkability: number | null;
  duplicateSpend: number | null;
  linkedPercent: number | null;
  coverage: number | null;
  status: string;
};

export type AdvertisingMetric = {
  key:
    | "advertisingSpend"
    | "linkedSpend"
    | "unlinkedSpend"
    | "roas"
    | "acos"
    | "adsHealth"
    | "trust"
    | "status";
  label: string;
  value: string;
  note: string;
  tone: StatusTone;
};

export type AdvertisingRecommendation = {
  id: string;
  campaign: string;
  recommendation: string;
  reason: string;
  expectedEffect: string;
  confidence: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
};

export type AdvertisingAlert = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type AdvertisingTimelineEvent = {
  id: string;
  title: string;
  description: string;
  period: "sync" | "analytics" | "import" | "health";
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type AdvertisingCampaign = {
  id: string;
  campaign: string;
  spend: number | null;
  revenue: number | null;
  roas: number | null;
  acos: number | null;
  status: string;
  recommendation: string;
};

export type AdvertisingSnapshot = {
  summary: AdvertisingSummary;
  health: AdvertisingHealth;
  metrics: AdvertisingMetric[];
  recommendations: AdvertisingRecommendation[];
  alerts: AdvertisingAlert[];
  timeline: AdvertisingTimelineEvent[];
  campaigns: AdvertisingCampaign[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
