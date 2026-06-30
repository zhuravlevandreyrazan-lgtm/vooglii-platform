import type { WorkspaceDiagnostics } from "@/shared/api";
import type { StatusTone } from "@/types/platform";

export type AutomationWorkspace =
  | "executive"
  | "business"
  | "finance"
  | "advertising"
  | "products"
  | "inventory"
  | "advisor"
  | "reports";

export type ExportFormat = "PDF" | "Excel" | "CSV" | "JSON";

export type AutomationStatus = {
  label: string;
  tone: StatusTone;
};

export type ExportPreset = {
  id: string;
  name: string;
  workspace: AutomationWorkspace;
  format: ExportFormat;
  description: string;
  owner: string;
  organizationName?: string | null;
  cabinetName?: string | null;
  status: AutomationStatus;
};

export type ScheduleItem = {
  id: string;
  name: string;
  workspace: AutomationWorkspace;
  enabled: boolean;
  time: string;
  timezone: string;
  cadence: string;
  format: ExportFormat;
  status: string;
  lastRunAt: string | null;
  nextRunAt: string | null;
  owner: string;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type JobItem = {
  id: string;
  type: string;
  workspace: AutomationWorkspace;
  status: string;
  progress: number;
  duration: string | null;
  startedAt: string | null;
  finishedAt: string | null;
  source: string;
  owner: string;
  message: string | null;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type ExportHistoryItem = {
  id: string;
  date: string | null;
  type: string;
  format: ExportFormat;
  size: string | null;
  status: string;
  source: string;
  owner: string;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type AutomationTimelineItem = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: string;
};

export type QuickActionItem = {
  id: string;
  label: string;
  workspace: AutomationWorkspace;
  format: ExportFormat;
  description: string;
};

export type AutomationSummary = {
  exportCount: number;
  scheduleCount: number;
  activeJobs: number;
  lastCompletedExport: string;
  schedulerHealth: string;
};

export type AutomationSnapshot = {
  summary: AutomationSummary;
  exports: ExportPreset[];
  schedules: ScheduleItem[];
  jobs: JobItem[];
  history: ExportHistoryItem[];
  timeline: AutomationTimelineItem[];
  quickActions: QuickActionItem[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
