"use client";

import type {
  AutomationSnapshot,
  AutomationTimelineItem,
  ExportFormat,
  ExportHistoryItem,
  ExportPreset,
  JobItem,
  QuickActionItem,
  ScheduleItem
} from "@/features/automation/types";
import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";

type RawExportRecord = {
  id?: string;
  name?: string;
  workspace?: string;
  format?: string;
  status?: string;
  source?: string;
  owner?: string;
  size?: string | null;
  createdAt?: string | null;
  organizationName?: string | null;
  cabinetName?: string | null;
};

type RawScheduleRecord = {
  id?: string;
  name?: string;
  workspace?: string;
  enabled?: boolean;
  time?: string;
  timezone?: string;
  cadence?: string;
  format?: string;
  status?: string;
  lastRunAt?: string | null;
  nextRunAt?: string | null;
  owner?: string;
  organizationName?: string | null;
  cabinetName?: string | null;
};

type RawJobRecord = {
  id?: string;
  type?: string;
  workspace?: string;
  status?: string;
  progress?: number;
  duration?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  source?: string;
  owner?: string;
  message?: string | null;
  organizationName?: string | null;
  cabinetName?: string | null;
};

type RawListResponse<T> = {
  exports?: T[];
  schedules?: T[];
  jobs?: T[];
};

const QUICK_ACTIONS: QuickActionItem[] = [
  { id: "qa-ceo", label: "Generate CEO Report", workspace: "executive", format: "PDF", description: "Prepare a leadership-facing operating snapshot." },
  { id: "qa-profit", label: "Generate Profit Audit", workspace: "finance", format: "CSV", description: "Create a profit reconciliation export bundle." },
  { id: "qa-finance", label: "Generate Finance Report", workspace: "finance", format: "JSON", description: "Create a finance-ready data handoff." },
  { id: "qa-ads", label: "Generate Advertising Report", workspace: "advertising", format: "CSV", description: "Export campaign efficiency and spend data." },
  { id: "qa-products", label: "Generate Products Report", workspace: "products", format: "JSON", description: "Package SKU-level product analytics." },
  { id: "qa-inventory", label: "Generate Inventory Report", workspace: "inventory", format: "CSV", description: "Export stock, restock, and supply state." },
  { id: "qa-advisor", label: "Generate Advisor Report", workspace: "advisor", format: "PDF", description: "Create an explainable advisor digest." }
];

function mapTone(status: string) {
  switch (status.toLowerCase()) {
    case "completed":
    case "ready":
    case "healthy":
      return "healthy" as const;
    case "running":
    case "queued":
    case "watch":
      return "watch" as const;
    case "failed":
    case "cancelled":
    case "error":
      return "risk" as const;
    default:
      return "neutral" as const;
  }
}

function normalizeFormat(value?: string): ExportFormat {
  if (value === "PDF" || value === "Excel" || value === "CSV" || value === "JSON") {
    return value;
  }
  return "JSON";
}

function normalizeExport(record: RawExportRecord): ExportPreset {
  const workspace = (record.workspace ?? "reports") as ExportPreset["workspace"];
  const status = record.status ?? "planned";
  return {
    id: record.id ?? `${workspace}-${record.format ?? "json"}`,
    name: record.name ?? "Export preset",
    workspace,
    format: normalizeFormat(record.format),
    description: `${record.name ?? "Export"} is ready to connect to a real exporter when backend generation becomes available.`,
    owner: record.owner ?? "VOOGLII Operator",
    organizationName: record.organizationName ?? null,
    cabinetName: record.cabinetName ?? null,
    status: {
      label: status,
      tone: mapTone(status)
    }
  };
}

function normalizeSchedule(record: RawScheduleRecord): ScheduleItem {
  return {
    id: record.id ?? "schedule-fallback",
    name: record.name ?? "Schedule placeholder",
    workspace: (record.workspace ?? "reports") as ScheduleItem["workspace"],
    enabled: Boolean(record.enabled),
    time: record.time ?? "09:00",
    timezone: record.timezone ?? "Europe/Moscow",
    cadence: record.cadence ?? "daily",
    format: normalizeFormat(record.format),
    status: record.status ?? "pending",
    lastRunAt: record.lastRunAt ?? null,
    nextRunAt: record.nextRunAt ?? null,
    owner: record.owner ?? "VOOGLII Operator",
    organizationName: record.organizationName ?? null,
    cabinetName: record.cabinetName ?? null
  };
}

function normalizeJob(record: RawJobRecord): JobItem {
  return {
    id: record.id ?? "job-fallback",
    type: record.type ?? "export",
    workspace: (record.workspace ?? "reports") as JobItem["workspace"],
    status: record.status ?? "queued",
    progress: typeof record.progress === "number" ? record.progress : 0,
    duration: record.duration ?? null,
    startedAt: record.startedAt ?? null,
    finishedAt: record.finishedAt ?? null,
    source: record.source ?? "dev",
    owner: record.owner ?? "VOOGLII Operator",
    message: record.message ?? null,
    organizationName: record.organizationName ?? null,
    cabinetName: record.cabinetName ?? null
  };
}

function buildHistory(exports: ExportPreset[], rawExports: RawExportRecord[]): ExportHistoryItem[] {
  return exports.map((item, index) => ({
    id: `${item.id}-history`,
    date: rawExports[index]?.createdAt ?? null,
    type: item.name,
    format: item.format,
    size: rawExports[index]?.size ?? null,
    status: item.status.label,
    source: rawExports[index]?.source ?? "dev",
    owner: item.owner,
    organizationName: rawExports[index]?.organizationName ?? item.organizationName ?? null,
    cabinetName: rawExports[index]?.cabinetName ?? item.cabinetName ?? null
  }));
}

function buildTimeline(exports: ExportPreset[], schedules: ScheduleItem[], jobs: JobItem[]): AutomationTimelineItem[] {
  const items: AutomationTimelineItem[] = [];

  if (exports[0]) {
    items.push({
      id: "automation-export-latest",
      title: `Latest export: ${exports[0].name}`,
      description: `${exports[0].format} export is tracked through the placeholder automation pipeline.`,
      severity: exports[0].status.tone === "risk" ? "high" : "info",
      source: "Export Pipeline"
    });
  }

  if (schedules[0]) {
    items.push({
      id: "automation-schedule-latest",
      title: `${schedules[0].name} schedule ${schedules[0].enabled ? "enabled" : "paused"}`,
      description: `Scheduler metadata is ready for a future cron or queue-backed scheduler.`,
      severity: schedules[0].enabled ? "low" : "medium",
      source: "Scheduler"
    });
  }

  if (jobs[0]) {
    items.push({
      id: "automation-job-latest",
      title: `Job ${jobs[0].id} is ${jobs[0].status}`,
      description: jobs[0].message ?? "Placeholder job lifecycle event.",
      severity: jobs[0].status === "failed" ? "critical" : jobs[0].status === "running" ? "medium" : "info",
      source: "Jobs Queue"
    });
  }

  return items;
}

function buildSummary(exports: ExportPreset[], schedules: ScheduleItem[], jobs: JobItem[]) {
  return {
    exportCount: exports.length,
    scheduleCount: schedules.length,
    activeJobs: jobs.filter((job) => ["running", "queued"].includes(job.status)).length,
    lastCompletedExport:
      exports.find((item) => item.status.label.toLowerCase() === "completed")?.name ?? "No completed exports yet",
    schedulerHealth: schedules.some((item) => item.status === "watch") ? "Watch" : "Healthy"
  };
}

const RAW_MOCK_EXPORTS: RawExportRecord[] = [
  { id: "export_ceo_daily", name: "CEO Report", workspace: "executive", format: "PDF", status: "completed", source: "demo", owner: "Daria Kuznetsova", size: "1.8 MB", createdAt: "2026-06-30T09:00:00Z" },
  { id: "export_profit_audit", name: "Profit Audit", workspace: "finance", format: "CSV", status: "completed", source: "demo", owner: "Daria Kuznetsova", size: "460 KB", createdAt: "2026-06-30T10:10:00Z" },
  { id: "export_advisor_digest", name: "Advisor Digest", workspace: "advisor", format: "JSON", status: "running", source: "demo", owner: "Daria Kuznetsova", size: null, createdAt: "2026-06-30T10:40:00Z" }
];

const RAW_MOCK_SCHEDULES: RawScheduleRecord[] = [
  { id: "schedule_ceo_daily", name: "CEO Daily", workspace: "executive", enabled: true, time: "09:00", timezone: "Europe/Moscow", cadence: "daily", format: "PDF", status: "healthy", lastRunAt: "2026-06-30T09:00:00Z", nextRunAt: "2026-07-01T09:00:00Z", owner: "Daria Kuznetsova" },
  { id: "schedule_monthly_business", name: "Monthly Business", workspace: "business", enabled: true, time: "08:30", timezone: "Europe/Moscow", cadence: "monthly", format: "JSON", status: "healthy", lastRunAt: "2026-06-01T08:30:00Z", nextRunAt: "2026-07-01T08:30:00Z", owner: "Daria Kuznetsova" },
  { id: "schedule_inventory_daily", name: "Inventory Daily", workspace: "inventory", enabled: false, time: "07:45", timezone: "Europe/Moscow", cadence: "daily", format: "CSV", status: "paused", lastRunAt: null, nextRunAt: null, owner: "Daria Kuznetsova" }
];

const RAW_MOCK_JOBS: RawJobRecord[] = [
  { id: "job_automation_001", type: "export", workspace: "executive", status: "completed", progress: 100, duration: "18s", startedAt: "2026-06-30T09:00:00Z", finishedAt: "2026-06-30T09:00:18Z", source: "demo", owner: "Daria Kuznetsova", message: "CEO report placeholder was prepared for the demo." },
  { id: "job_automation_002", type: "scheduler", workspace: "finance", status: "running", progress: 64, duration: "31s", startedAt: "2026-06-30T10:42:00Z", finishedAt: null, source: "demo", owner: "Daria Kuznetsova", message: "Finance daily schedule is building a placeholder job bundle." },
  { id: "job_automation_003", type: "export", workspace: "advertising", status: "failed", progress: 100, duration: "11s", startedAt: "2026-06-30T08:10:00Z", finishedAt: "2026-06-30T08:10:11Z", source: "demo", owner: "Daria Kuznetsova", message: "Exporter is intentionally placeholder-only in this phase." }
];

export function normalizeAutomationSnapshot(
  raw: {
    exports: RawExportRecord[];
    schedules: RawScheduleRecord[];
    jobs: RawJobRecord[];
    lastUpdated?: string | null;
  },
  diagnostics = createFallbackDiagnostics()
): AutomationSnapshot {
  const exports = raw.exports.map(normalizeExport);
  const schedules = raw.schedules.map(normalizeSchedule);
  const jobs = raw.jobs.map(normalizeJob);

  return {
    summary: buildSummary(exports, schedules, jobs),
    exports,
    schedules,
    jobs,
    history: buildHistory(exports, raw.exports),
    timeline: buildTimeline(exports, schedules, jobs),
    quickActions: QUICK_ACTIONS,
    lastUpdated: raw.lastUpdated ?? raw.exports[0]?.createdAt ?? new Date().toISOString(),
    diagnostics
  };
}

export function getAutomationMockSnapshot() {
  return normalizeAutomationSnapshot({
    exports: RAW_MOCK_EXPORTS,
    schedules: RAW_MOCK_SCHEDULES,
    jobs: RAW_MOCK_JOBS,
    lastUpdated: "2026-06-30T10:45:00Z"
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function fetchAutomationSnapshot(signal?: AbortSignal) {
  const [exportsPayload, schedulesPayload, jobsPayload] = await Promise.all([
    requestJson<unknown>(apiEndpoints.exports, { signal }),
    requestJson<unknown>(apiEndpoints.schedules, { signal }),
    requestJson<unknown>(apiEndpoints.jobs, { signal })
  ]);

  const exportsRecord = assertWorkspacePayload(exportsPayload, apiEndpoints.exports, "Exports");
  const schedulesRecord = assertWorkspacePayload(schedulesPayload, apiEndpoints.schedules, "Schedules");
  const jobsRecord = assertWorkspacePayload(jobsPayload, apiEndpoints.jobs, "Jobs");

  if (!isRecord(exportsRecord) || !isRecord(schedulesRecord) || !isRecord(jobsRecord)) {
    throw new ApiError("Automation API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.exports
    });
  }

  const runtime = normalizeRuntimeMetadata(exportsRecord) ?? normalizeRuntimeMetadata(schedulesRecord) ?? normalizeRuntimeMetadata(jobsRecord);

  return normalizeAutomationSnapshot(
    {
      exports: Array.isArray(exportsRecord.exports) ? (exportsRecord.exports as RawExportRecord[]) : [],
      schedules: Array.isArray(schedulesRecord.schedules) ? (schedulesRecord.schedules as RawScheduleRecord[]) : [],
      jobs: Array.isArray(jobsRecord.jobs) ? (jobsRecord.jobs as RawJobRecord[]) : [],
      lastUpdated: new Date().toISOString()
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}

export async function generateExportPreset(payload: {
  workspace: string;
  format: ExportFormat;
  name?: string;
  sku?: string;
}) {
  const response = await requestJson<unknown>(apiEndpoints.exports, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const record = assertWorkspacePayload(response, apiEndpoints.exports, "Export Create");
  const exportRecord = isRecord(record.export) ? (record.export as RawExportRecord) : null;
  if (!exportRecord) {
    throw new ApiError("Export create payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.exports
    });
  }
  return normalizeExport(exportRecord);
}

export async function updateScheduleState(scheduleId: string, payload: Record<string, unknown>) {
  const response = await requestJson<unknown>(`${apiEndpoints.schedules}/${scheduleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const record = assertWorkspacePayload(response, `${apiEndpoints.schedules}/${scheduleId}`, "Schedule Update");
  const scheduleRecord = isRecord(record.schedule) ? (record.schedule as RawScheduleRecord) : null;
  if (!scheduleRecord) {
    throw new ApiError("Schedule update payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: `${apiEndpoints.schedules}/${scheduleId}`
    });
  }
  return normalizeSchedule(scheduleRecord);
}
