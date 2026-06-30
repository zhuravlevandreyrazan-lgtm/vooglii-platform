import type { StatusTone } from "@/types/platform";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type ProductDetailsStatus = {
  label: string;
  tone: StatusTone;
};

export type ProductEvidence = {
  id: string;
  label: string;
  detail: string;
  source: "backend" | "placeholder";
};

export type ProductOverview = {
  sku: string;
  name: string;
  imageUrl: string | null;
  category: string;
  brand: string;
  vendorCode: string;
  status: ProductDetailsStatus;
  health: string;
  healthScore: number | null;
  abc: string;
  xyz: string;
};

export type ProductSales = {
  revenue: number | null;
  orders: number | null;
  units: number | null;
  averagePrice: number | null;
  trend: string;
};

export type ProductFinance = {
  profit: number | null;
  margin: number | null;
  expenses: number | null;
  officialProfit: number | null;
  difference: number | null;
};

export type ProductAdvertising = {
  spend: number | null;
  roas: number | null;
  acos: number | null;
  campaignCount: number | null;
  adsHealth: string;
};

export type ProductInventory = {
  stock: number | null;
  reserved: number | null;
  available: number | null;
  daysLeft: number | null;
  forecast: string;
  warehouse: string;
};

export type ProductForecast = {
  summary: string;
  confidence: string;
  nextReorderDate: string | null;
};

export type ProductHistory = {
  period: "today" | "sevenDays" | "thirtyDays" | "ninetyDays";
  revenue: number | null;
  profit: number | null;
  orders: number | null;
  note: string;
};

export type ProductRecommendation = {
  id: string;
  priority: "critical" | "high" | "medium" | "low" | "info";
  reason: string;
  expectedEffect: string;
  confidence: string;
};

export type ProductAction = {
  id: string;
  label: string;
  href: string | null;
  type: "link" | "button";
  enabled: boolean;
};

export type ProductTimeline = {
  id: string;
  title: string;
  description: string;
  period: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type ProductInsight = {
  summary: string;
  topRisk: string;
  topOpportunity: string;
  recommendation: string;
  evidence: ProductEvidence[];
};

export type ProductDeepLink = {
  id: string;
  label: string;
  href: string;
  description: string;
};

export type ProductDetailsSnapshot = {
  overview: ProductOverview;
  sales: ProductSales;
  finance: ProductFinance;
  advertising: ProductAdvertising;
  inventory: ProductInventory;
  forecast: ProductForecast;
  history: ProductHistory[];
  recommendations: ProductRecommendation[];
  timeline: ProductTimeline[];
  insight: ProductInsight;
  quickActions: ProductAction[];
  deepLinks: ProductDeepLink[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
