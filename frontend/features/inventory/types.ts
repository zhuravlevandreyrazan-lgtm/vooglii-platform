import type { StatusTone } from "@/types/platform";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type InventorySummary = {
  totalStock: number | null;
  criticalSku: number | null;
  daysLeftAverage: number | null;
  forecastCoverage: number | null;
  inventoryHealth: string;
  warehouseCount: number | null;
  lastUpdated: string | null;
};

export type InventoryHealth = {
  inventoryHealth: string;
  coverage: number | null;
  forecastConfidence: string;
  criticalStock: number | null;
  lowStock: number | null;
  warehouseStatus: string;
};

export type InventoryForecast = {
  sku: string;
  forecast: string;
  expectedCoverage: string;
};

export type InventoryWarehouse = {
  id: string;
  warehouse: string;
  currentStock: number | null;
  criticalSku: number | null;
  forecast: string;
  health: string;
  status: string;
};

export type InventorySku = {
  sku: string;
  stock: number | null;
  reserved: number | null;
  available: number | null;
  daysLeft: number | null;
  forecast: string;
  warehouse: string;
  health: string;
  priority: string;
  recommendation: string;
  status: {
    label: string;
    tone: StatusTone;
  };
};

export type InventoryPriority = {
  id: string;
  level: "critical" | "high" | "medium" | "low";
  reason: string;
  recommendation: string;
};

export type InventoryAlert = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type InventoryTimeline = {
  id: string;
  title: string;
  description: string;
  period: "import" | "forecast" | "restock" | "sync";
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: "backend" | "placeholder";
};

export type InventoryHistory = {
  period: "today" | "sevenDays" | "thirtyDays" | "ninetyDays";
  stock: number | null;
  coverage: number | null;
  note: string;
};

export type InventoryMetrics = {
  label: string;
  value: string;
  note: string;
  tone: StatusTone;
};

export type InventoryRestockPlan = {
  id: string;
  sku: string;
  recommendedQuantity: number | null;
  priority: "critical" | "high" | "medium" | "low" | "info";
  reason: string;
  expectedCoverage: string;
  warehouse: string;
};

export type InventorySnapshot = {
  summary: InventorySummary;
  health: InventoryHealth;
  items: InventorySku[];
  restockPlan: InventoryRestockPlan[];
  supplyPriority: InventoryPriority[];
  warehouses: InventoryWarehouse[];
  history: InventoryHistory[];
  alerts: InventoryAlert[];
  timeline: InventoryTimeline[];
  metrics: InventoryMetrics[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
