import {
  apiEndpoints,
  ApiError,
  getApiBaseUrl,
  normalizeApiBaseUrl,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";
import { commandCenterMock } from "@/shared/data/mock-platform";
import {
  localizeKnownText,
  localizeRuntimeSource,
  localizeStatus,
  localizeWorkspaceLabel,
  sanitizeUserText,
  sanitizeUserTextList
} from "@/shared/ui/status-labels";
import {
  mapDecisionEngineApiResponse,
  type ApiDecisionEngineResponse
} from "@/services/decision-engine-api";
import type {
  CommandCenterRuntimeSource,
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
  decision_engine?: ApiDecisionEngineResponse | null;
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
  runtime?: {
    source?: string;
    degraded?: boolean;
    cached?: boolean;
    stale?: boolean;
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

  if ("decision_engine" in value && value.decision_engine !== undefined && value.decision_engine !== null && !isObject(value.decision_engine)) {
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
    return "Средняя уверенность";
  }
  if (value >= 85) {
    return "Высокая уверенность";
  }
  if (value >= 65) {
    return "Средняя уверенность";
  }
  return "Низкая уверенность";
}

export function mapCommandCenterApiResponseToSnapshot(
  payload: ApiCommandCenterResponse
): CommandCenterSnapshot {
  const summaryBits = [
    ...(payload.executive_brief?.what_happened ?? []),
    ...(payload.executive_brief?.why ?? [])
  ].filter(Boolean);
  const executiveSummary = sanitizeUserTextList(summaryBits, "").join(" ");
  const businessSummary = sanitizeUserText(payload.business_health?.summary, "");
  const sourceSummary =
    executiveSummary || businessSummary || "Данные появятся после первой синхронизации.";
  const sanitizedSources = sanitizeUserTextList(payload.executive_brief?.sources, "");
  const runtimeDescription = payload.system?.degraded
    ? "Часть модулей временно недоступна, но платформа продолжает показывать подтвержденные данные."
    : "Данные получены из рабочего контура и обновлены для текущего экрана.";

  return {
    businessHealth: {
      score: typeof payload.business_health?.score === "number" ? payload.business_health.score : null,
      status: localizeStatus(payload.business_health?.status ?? "UNKNOWN"),
      summary: sourceSummary
    },
    decisionEngine: payload.decision_engine ? mapDecisionEngineApiResponse(payload.decision_engine) : null,
    executiveBrief: {
      id: "executive-brief",
      eyebrow: "Краткий вывод",
      title: sanitizeUserText(payload.executive_brief?.title, "Сводка появится после загрузки данных"),
      summary: sourceSummary,
      confidence: formatConfidence(payload.executive_brief?.confidence),
      sources: sanitizedSources,
      tone: statusToTone(payload.business_health?.status)
    },
    kpis:
      payload.kpis?.map((metric) => ({
        label: sanitizeUserText(metric.title, "Показатель"),
        value: sanitizeUserText(metric.value, "Нет данных"),
        delta: sanitizeUserText(metric.delta, "Нет данных"),
        tone: statusToTone(metric.status),
        note: "Актуальные показатели по выбранному периоду"
      })) ?? [],
    timeline:
      payload.recent_events?.map((event, index) => ({
        id: event.id ?? `timeline-${index + 1}`,
        time: "Сейчас",
        title: localizeKnownText(event.title, "Последнее событие"),
        detail: localizeKnownText(event.detail, "Подробности появятся после обновления данных."),
        tone: statusToTone(event.status)
      })) ?? [],
    actions:
      payload.today_actions?.map((action, index) => ({
        id: action.id ?? `action-${index + 1}`,
        title: sanitizeUserText(action.title, "Действие"),
        owner: sanitizeUserText(action.owner, "Центр управления"),
        eta: sanitizeUserText(action.eta, "Сегодня"),
        tone: statusToTone(action.status)
      })) ?? [],
    alerts:
      payload.critical_alerts?.map((alert, index) => ({
        id: alert.id ?? `alert-${index + 1}`,
        title: localizeKnownText(alert.title, "Сигнал"),
        detail: localizeKnownText(alert.detail, "Подробности появятся после обновления данных."),
        tone: statusToTone(alert.status)
      })) ?? [],
    workspaces:
      payload.workspaces?.map((workspace) => ({
        title: localizeWorkspaceLabel(workspace.title ?? "workspace"),
        href: workspace.href ?? "/",
        summary: localizeKnownText(workspace.summary, "Раздел будет доступен после загрузки данных."),
        status: localizeStatus(workspace.status ?? "UNKNOWN")
      })) ?? commandCenterMock.workspaces,
    notifications: [
      {
        id: "api-source",
        title: localizeRuntimeSource(payload.runtime?.source ?? "live"),
        description: runtimeDescription,
        tone: statusToTone(payload.business_health?.status)
      },
      {
        id: "api-period",
        title: payload.period?.label === "current_month" ? "Текущий месяц" : "Отчетный период",
        description: `${payload.period?.date_from ?? "?"} - ${payload.period?.date_to ?? "?"}`,
        tone: "neutral"
      }
    ]
  };
}

export function getCommandCenterMockSnapshot(): CommandCenterScreenData {
  return {
    snapshot: commandCenterMock,
    source: "mock_fallback",
    runtimeSource: "fallback",
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

  const runtime = normalizeRuntimeMetadata(payload as Record<string, unknown>);
  return {
    snapshot,
    source: "real",
    runtimeSource: runtime?.source as CommandCenterRuntimeSource | undefined,
    apiBaseUrl: getApiBaseUrl()
  };
}

export async function getCommandCenterApiSnapshot(signal?: AbortSignal): Promise<CommandCenterScreenData> {
  return fetchCommandCenterApiSnapshot(signal);
}
