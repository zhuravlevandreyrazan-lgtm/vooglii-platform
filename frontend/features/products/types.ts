import type { StatusTone } from "@/types/platform";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type ProductSummary = {
  skuCount: number;
  activeSku: number;
  problemSku: number;
  riskSku: number;
  growthSku: number;
  lastUpdated: string | null;
};

export type ProductMetrics = {
  revenue: number | null;
  profit: number | null;
  margin: number | null;
  roas: number | null;
  acos: number | null;
  stock: number | null;
  daysLeft: number | null;
};

export type ProductHealth = {
  health: string;
  status: string;
  abc: string;
  xyz: string;
  forecast: string;
  riskLevel: string;
};

export type ProductStatus = {
  label: string;
  tone: StatusTone;
};

export type ProductForecast = {
  period: "today" | "sevenDays" | "thirtyDays" | "ninetyDays";
  sales: number | null;
  advertising: number | null;
  note: string;
};

export type ProductRecommendation = {
  id: string;
  sku: string;
  recommendation: string;
  reason: string;
  priority: "critical" | "high" | "medium" | "low" | "info";
  confidence: string;
  expectedEffect: string;
};

export type ProductHistory = {
  period: "today" | "sevenDays" | "thirtyDays" | "ninetyDays";
  sales: number | null;
  advertising: number | null;
  note: string;
};

export type ProductAction = {
  id: string;
  sku: string;
  action: string;
  status: string;
};

export type ProductTimeline = {
  id: string;
  title: string;
  description: string;
  period: "sync" | "import" | "audit" | "forecast";
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type ProductAlert = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type ProductCard = {
  sku: string;
  name: string;
  metrics: ProductMetrics;
  health: ProductHealth;
  status: ProductStatus;
  recommendation: string;
  trend: string;
  warehouse: string;
};

export type ProductSnapshot = {
  summary: ProductSummary;
  products: ProductCard[];
  recommendations: ProductRecommendation[];
  history: ProductHistory[];
  inventoryPreview: ProductCard[];
  alerts: ProductAlert[];
  timeline: ProductTimeline[];
  actions: ProductAction[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
