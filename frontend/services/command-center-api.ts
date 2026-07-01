import { commandCenterMock } from "@/shared/data/mock-platform";
import {
  apiEndpoints,
  ApiError,
  getApiBaseUrl,
  normalizeApiBaseUrl,
  requestJson
} from "@/shared/api";
import type {
  CommandCenterScreenData,
  CommandCenterSnapshot,
  StatusTone
} from "@/types/platform";

type ApiStatus = "GOOD" | "WARNING" | "CRITICAL" | "UNKNOWN";

export type ApiCommandCenterResponse = {
  product: string;
  screen: string;
  period?: {
    label?: string;
    date_from?: string;
    date_to?: string;
  };
  business_health?: {
    score?: number;
    status?: ApiStatus;
    summary?: string;
    confidence?: number;
    data_mode?: string;
  };
  executive_brief?: {
    title?: string;
    what_happened?: string[];
    why?: string[];
    actions?: string[];
    confidence?: number;
    sources?: string[];
  };
  kpis?: Array<{
    id?: string;
    title?: string;
    value?: string;
    delta?: string;
    status?: ApiStatus;
    source?: string;
  }>;
  workspaces?: Array<{
    title?: string;
    href?: string;
    summary?: string;
    status?: string;
  }>;
  today_actions?: Array<{
    id?: string;
    title?: string;
    owner?: string;
    eta?: string;
    status?: ApiStatus;
  }>;
  critical_alerts?: Array<{
    id?: string;
    title?: string;
    detail?: string;
    status?: ApiStatus;
  }>;
  recent_events?: Array<{
    id?: string;
    title?: string;
    detail?: string;
    status?: ApiStatus;
  }>;
  system?: {
    status?: string;
    finance_api?: string;
    last_updated?: string;
    degraded?: boolean;
    degraded_notes?: string[];
  };
};

export function normalizeCommandCenterApiBaseUrl(value?: string) {
  return normalizeApiBaseUrl(value);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

export function isApiCommandCenterResponse(value: unknown): value is ApiCommandCenterResponse {
  if (!isObject(value)) {
    return false;
  }

  if (value.product !== "VOOGLII" || value.screen !== "command_center") {
    return false;
  }

  if ("kpis" in value && value.kpis !== undefined && !Array.isArray(value.kpis)) {
    return false;
  }

  if ("workspaces" in value && value.workspaces !== undefined && !Array.isArray(value.workspaces)) {
    return false;
  }

  if (
    "executive_brief" in value &&
    value.executive_brief !== undefined &&
    (!isObject(value.executive_brief) ||
      ("what_happened" in value.executive_brief &&
        value.executive_brief.what_happened !== undefined &&
        !isStringArray(value.executive_brief.what_happened)) ||
      ("why" in value.executive_brief &&
        value.executive_brief.why !== undefined &&
        !isStringArray(value.executive_brief.why)) ||
      ("actions" in value.executive_brief &&
        value.executive_brief.actions !== undefined &&
        !isStringArray(value.executive_brief.actions)) ||
      ("sources" in value.executive_brief &&
        value.executive_brief.sources !== undefined &&
        !isStringArray(value.executive_brief.sources)))
  ) {
    return false;
  }

  return true;
}

function statusToTone(status?: string): StatusTone {
  switch ((status ?? "").toUpperCase()) {
    case "GOOD":
    case "OK":
    case "READY":
      return "healthy";
    case "WARNING":
    case "PARTIAL":
      return "watch";
    case "CRITICAL":
    case "BLOCKED":
    case "ERROR":
      return "risk";
    default:
      return "neutral";
  }
}

function formatConfidence(value?: number) {
  if (typeof value !== "number") {
    return "Partial confidence";
  }
  if (value >= 85) {
    return "High confidence";
  }
  if (value >= 65) {
    return "Medium confidence";
  }
  return "Low confidence";
}

export function mapCommandCenterApiResponseToSnapshot(
  payload: ApiCommandCenterResponse
): CommandCenterSnapshot {
  const summaryBits = [
    ...(payload.executive_brief?.what_happened ?? []),
    ...(payload.executive_brief?.why ?? [])
  ].filter(Boolean);
  const systemFinance = payload.system?.finance_api ?? "UNKNOWN";
  const degraded = payload.system?.degraded ? " Degraded fields are active." : "";

  return {
    businessHealth: {
      score: payload.business_health?.score ?? commandCenterMock.businessHealth.score,
      status: payload.business_health?.status ?? "UNKNOWN",
      summary:
        payload.business_health?.summary ??
        summaryBits[0] ??
        commandCenterMock.businessHealth.summary
    },
    executiveBrief: {
      id: "executive-brief",
      eyebrow: "Executive Brief",
      title: payload.executive_brief?.title ?? commandCenterMock.executiveBrief.title,
      summary:
        summaryBits.join(" ").trim() ||
        payload.business_health?.summary ||
        commandCenterMock.executiveBrief.summary,
      confidence: formatConfidence(payload.executive_brief?.confidence),
      sources:
        payload.executive_brief?.sources?.length
          ? payload.executive_brief.sources
          : commandCenterMock.executiveBrief.sources,
      tone: statusToTone(payload.business_health?.status)
    },
    kpis:
      payload.kpis?.map((metric) => ({
        label: metric.title ?? "KPI",
        value: metric.value ?? "n/a",
        delta: metric.delta ?? "n/a",
        tone: statusToTone(metric.status),
        note: metric.source ?? "Live backend API"
      })) ?? commandCenterMock.kpis,
    timeline:
      payload.recent_events?.map((event, index) => ({
        id: event.id ?? `timeline-${index + 1}`,
        time: "Now",
        title: event.title ?? "Recent event",
        detail: event.detail ?? "No detail available.",
        tone: statusToTone(event.status)
      })) ?? commandCenterMock.timeline,
    actions:
      payload.today_actions?.map((action, index) => ({
        id: action.id ?? `action-${index + 1}`,
        title: action.title ?? "Action",
        owner: action.owner ?? "Command Center",
        eta: action.eta ?? "Today",
        tone: statusToTone(action.status)
      })) ?? commandCenterMock.actions,
    alerts:
      payload.critical_alerts?.map((alert, index) => ({
        id: alert.id ?? `alert-${index + 1}`,
        title: alert.title ?? "Alert",
        detail: alert.detail ?? "No detail available.",
        tone: statusToTone(alert.status)
      })) ?? commandCenterMock.alerts,
    workspaces:
      payload.workspaces?.map((workspace) => ({
        title: workspace.title ?? "Workspace",
        href: workspace.href ?? "/",
        summary: workspace.summary ?? "Read-only workspace",
        status: workspace.status ?? "UNKNOWN"
      })) ?? commandCenterMock.workspaces,
    notifications: [
      {
        id: "api-source",
        title: "Live backend connected",
        description: `Finance API status: ${systemFinance}.${degraded}`,
        tone: statusToTone(payload.business_health?.status)
      },
      {
        id: "api-period",
        title: payload.period?.label === "current_month" ? "Current month snapshot" : "Snapshot window",
        description: `${payload.period?.date_from ?? "?"} to ${payload.period?.date_to ?? "?"}`,
        tone: "neutral"
      }
    ]
  };
}

export function getCommandCenterMockSnapshot(): CommandCenterScreenData {
  return {
    snapshot: commandCenterMock,
    source: "mock_fallback",
    apiBaseUrl: getApiBaseUrl()
  };
}

export function parseCommandCenterApiPayload(payload: unknown) {
  if (!isApiCommandCenterResponse(payload)) {
    throw new Error("Parsed JSON does not match expected command-center schema");
  }

  return mapCommandCenterApiResponseToSnapshot(payload);
}

export async function fetchCommandCenterApiSnapshot(
  signal?: AbortSignal
): Promise<CommandCenterScreenData> {
  const payload = await requestJson<unknown>(apiEndpoints.commandCenter, { signal });

  let snapshot: CommandCenterSnapshot;

  try {
    snapshot = parseCommandCenterApiPayload(payload);
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : "Parsed JSON does not match expected command-center schema",
      {
        code: "invalid_shape",
        status: null,
        url: apiEndpoints.commandCenter
      },
      error
    );
  }

  return {
    snapshot,
    source: "real",
    apiBaseUrl: getApiBaseUrl()
  };
}

export async function getCommandCenterApiSnapshot(signal?: AbortSignal): Promise<CommandCenterScreenData> {
  return fetchCommandCenterApiSnapshot(signal);
}
