import type { WorkspaceDiagnostics } from "@/shared/api";
import type { StatusTone } from "@/types/platform";

export type ReportCategory =
  | "executive"
  | "finance"
  | "advertising"
  | "products"
  | "inventory"
  | "business"
  | "advisor"
  | "system";

export type ReportStatus = {
  label: string;
  tone: StatusTone;
};

export type ReportItem = {
  id: string;
  name: string;
  description: string;
  category: ReportCategory;
  status: ReportStatus;
  updatedAt: string | null;
  source: string;
  href: string;
};

export type ReportHistory = {
  id: string;
  date: string | null;
  type: string;
  status: string;
  source: string;
  href: string;
};

export type ReportExport = {
  format: "PDF" | "Excel" | "CSV" | "JSON";
  status: string;
  description: string;
};

export type ReportTemplate = {
  id: string;
  name: string;
  category: ReportCategory;
  status: string;
};

export type ReportTimeline = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: string;
};

export type ReportSource = {
  module: ReportCategory;
  health: string;
  status: string;
  lastUpdated: string | null;
};

export type ReportSummary = {
  reportCount: number;
  latestReport: string;
  latestSync: string;
  latestCeoReport: string;
  latestProfitAudit: string;
  systemStatus: string;
};

export type ReportsSnapshot = {
  summary: ReportSummary;
  catalog: ReportItem[];
  recent: ReportHistory[];
  templates: ReportTemplate[];
  exports: ReportExport[];
  timeline: ReportTimeline[];
  sources: ReportSource[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
