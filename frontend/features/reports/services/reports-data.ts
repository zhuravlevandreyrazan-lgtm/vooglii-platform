import type {
  ReportExport,
  ReportHistory,
  ReportItem,
  ReportSource,
  ReportTemplate,
  ReportsSnapshot
} from "@/features/reports/types";
import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";

type RawReportsSnapshot = {
  summary?: Partial<ReportsSnapshot["summary"]>;
  catalog?: ReportItem[];
  recent?: ReportHistory[];
  templates?: ReportTemplate[];
  exports?: ReportExport[];
  timeline?: ReportsSnapshot["timeline"];
  sources?: ReportSource[];
  lastUpdated?: string | null;
};

const rawReportsSnapshot: RawReportsSnapshot = {
  summary: {
    reportCount: 11,
    latestReport: "Advisor Snapshot",
    latestSync: "2026-06-30 14:30",
    latestCeoReport: "CEO Report",
    latestProfitAudit: "Profit Audit",
    systemStatus: "Operational"
  },
  catalog: [
    {
      id: "report-ceo",
      name: "CEO Report",
      description: "Leadership-facing report from the analytics engine.",
      category: "executive",
      status: { label: "Ready", tone: "healthy" },
      updatedAt: "2026-06-30T14:20:00.000Z",
      source: "Analytics Engine",
      href: "/executive"
    },
    {
      id: "report-profit-audit",
      name: "Profit Audit",
      description: "Finance-safe profit audit and reconciliation report.",
      category: "finance",
      status: { label: "Ready", tone: "watch" },
      updatedAt: "2026-06-30T14:12:00.000Z",
      source: "Finance Engine",
      href: "/finance"
    },
    {
      id: "report-ads",
      name: "Advertising Analytics",
      description: "Campaign efficiency, linkability, and ads health analytics.",
      category: "advertising",
      status: { label: "Ready", tone: "healthy" },
      updatedAt: "2026-06-30T14:14:00.000Z",
      source: "Advertising Engine",
      href: "/advertising"
    },
    {
      id: "report-sku",
      name: "SKU Analytics",
      description: "Product intelligence and SKU analytics report set.",
      category: "products",
      status: { label: "Ready", tone: "healthy" },
      updatedAt: "2026-06-30T14:16:00.000Z",
      source: "Product Engine",
      href: "/products"
    }
  ],
  recent: [
    {
      id: "recent-1",
      date: "2026-06-30T14:20:00.000Z",
      type: "Advisor Snapshot",
      status: "Generated",
      source: "Advisor Engine",
      href: "/advisor"
    },
    {
      id: "recent-2",
      date: "2026-06-30T14:12:00.000Z",
      type: "Profit Audit",
      status: "Generated",
      source: "Finance Engine",
      href: "/finance"
    }
  ],
  templates: [
    { id: "template-ceo", name: "CEO", category: "executive", status: "Ready" },
    { id: "template-finance", name: "Finance", category: "finance", status: "Ready" },
    { id: "template-ads", name: "Advertising", category: "advertising", status: "Ready" },
    { id: "template-business", name: "Business", category: "business", status: "Ready" },
    { id: "template-inventory", name: "Inventory", category: "inventory", status: "Ready" },
    { id: "template-products", name: "Products", category: "products", status: "Ready" },
    { id: "template-advisor", name: "Advisor", category: "advisor", status: "Ready" }
  ],
  exports: [
    { format: "PDF", status: "Planned", description: "Architecture ready for future PDF export." },
    { format: "Excel", status: "Planned", description: "Architecture ready for future Excel export." },
    { format: "CSV", status: "Planned", description: "Architecture ready for future CSV export." },
    { format: "JSON", status: "Planned", description: "Architecture ready for future JSON export." }
  ],
  timeline: [
    {
      id: "reports-timeline-1",
      title: "Latest reports sync completed",
      description: "Reports catalog has been refreshed from backend-ready report metadata.",
      severity: "info",
      source: "Report Engine"
    },
    {
      id: "reports-timeline-2",
      title: "Latest CEO Report registered",
      description: "CEO report metadata was updated in the reports center.",
      severity: "low",
      source: "Analytics Engine"
    }
  ],
  sources: [
    { module: "executive", health: "Healthy", status: "Active", lastUpdated: "2026-06-30T14:20:00.000Z" },
    { module: "business", health: "Healthy", status: "Active", lastUpdated: "2026-06-30T14:10:00.000Z" },
    { module: "finance", health: "Watch", status: "Degraded", lastUpdated: "2026-06-30T14:12:00.000Z" },
    { module: "advertising", health: "Watch", status: "Active", lastUpdated: "2026-06-30T14:14:00.000Z" },
    { module: "products", health: "Healthy", status: "Active", lastUpdated: "2026-06-30T14:16:00.000Z" },
    { module: "inventory", health: "Watch", status: "Active", lastUpdated: "2026-06-30T14:18:00.000Z" },
    { module: "advisor", health: "Healthy", status: "Active", lastUpdated: "2026-06-30T14:20:00.000Z" },
    { module: "system", health: "Healthy", status: "Operational", lastUpdated: "2026-06-30T14:22:00.000Z" }
  ],
  lastUpdated: "2026-06-30T14:30:00.000Z"
};

export function normalizeReportsSnapshot(
  raw: RawReportsSnapshot,
  diagnostics = createFallbackDiagnostics()
): ReportsSnapshot {
  return {
    summary: {
      reportCount: raw.summary?.reportCount ?? 0,
      latestReport: raw.summary?.latestReport ?? "No reports yet",
      latestSync: raw.summary?.latestSync ?? "n/a",
      latestCeoReport: raw.summary?.latestCeoReport ?? "n/a",
      latestProfitAudit: raw.summary?.latestProfitAudit ?? "n/a",
      systemStatus: raw.summary?.systemStatus ?? "Unknown"
    },
    catalog:
      raw.catalog?.length
        ? raw.catalog
        : [
            {
              id: "report-fallback",
              name: "Reports catalog pending",
              description: "No backend-ready reports were returned in the current snapshot.",
              category: "system",
              status: { label: "Pending", tone: "neutral" },
              updatedAt: null,
              source: "Report Engine",
              href: "/reports"
            }
          ],
    recent:
      raw.recent?.length
        ? raw.recent
        : [
            {
              id: "recent-fallback",
              date: null,
              type: "No recent reports",
              status: "Pending",
              source: "Report Engine",
              href: "/reports"
            }
          ],
    templates: raw.templates ?? [],
    exports: raw.exports ?? [],
    timeline:
      raw.timeline?.length
        ? raw.timeline
        : [
            {
              id: "reports-timeline-fallback",
              title: "Reports timeline is waiting for backend events",
              description: "No report timeline entries are available yet.",
              severity: "info",
              source: "Report Engine"
            }
          ],
    sources: raw.sources ?? [],
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getReportsMockSnapshot() {
  return normalizeReportsSnapshot(rawReportsSnapshot);
}

function isRawReportsSnapshot(value: unknown): value is RawReportsSnapshot {
  return typeof value === "object" && value !== null;
}

export async function fetchReportsSnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.reports, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.reports, "Reports");

  if (!isRawReportsSnapshot(record)) {
    throw new ApiError("Reports API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.reports
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeReportsSnapshot(
    record,
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
