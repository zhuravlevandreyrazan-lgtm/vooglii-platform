import type {
  DecisionEngineAction,
  DecisionEngineChange,
  DecisionEngineEvidence,
  DecisionEngineForecast,
  DecisionEngineSnapshot
} from "@/features/decision-engine/types";
import { apiEndpoints, ApiError, requestJson } from "@/shared/api";
import {
  localizeKnownText,
  localizeStatus,
  sanitizeUserText,
  sanitizeUserTextList
} from "@/shared/ui/status-labels";
import type { StatusTone } from "@/types/platform";

type ApiDecisionSignal = {
  id?: string;
  type?: string;
  label?: string;
  title?: string;
  message?: string;
  severity?: string;
  priority?: string;
  expectedImpact?: string;
  confidence?: number | string | null;
  reason?: string;
  action?: string;
  source?: string;
};

export type ApiDecisionEngineResponse = {
  summary?: {
    title?: string;
    status?: string;
    code?: string;
    message?: string;
    confidence?: number | string | null;
  };
  whatChanged?: Array<{
    id?: string;
    type?: string;
    title?: string;
    message?: string;
    severity?: string;
    confidence?: number | string | null;
    source?: string;
  }>;
  mainRisk?: ApiDecisionSignal | null;
  mainOpportunity?: ApiDecisionSignal | null;
  todayActions?: ApiDecisionSignal[];
  forecast?: {
    status?: string;
    message?: string;
    profit?: number | string | null;
    profitDirection?: string | null;
    riskLevel?: string | null;
    expectedImpact?: string | null;
    confidence?: number | string | null;
  };
  evidence?: Array<{
    label?: string;
    metric?: string;
    value?: unknown;
    source?: string;
    confidence?: number | string | null;
    reason?: string;
  }>;
  sources?: string[];
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function statusToTone(status?: string): StatusTone {
  switch ((status ?? "").toUpperCase()) {
    case "GOOD":
    case "READY":
    case "OK":
      return "healthy";
    case "WARNING":
    case "PARTIAL":
    case "WATCH":
      return "watch";
    case "CRITICAL":
    case "BLOCKED":
    case "ERROR":
      return "risk";
    default:
      return "neutral";
  }
}

function formatConfidence(value?: number | string | null): string {
  if (typeof value === "number") {
    if (value >= 85) return "Высокая уверенность";
    if (value >= 65) return "Средняя уверенность";
    if (value > 0) return "Низкая уверенность";
    return "Недостаточно данных";
  }
  const text = sanitizeUserText(typeof value === "string" ? value : "", "");
  return text || "Недостаточно данных";
}

function formatMetricValue(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
  }
  return sanitizeUserText(typeof value === "string" ? value : "", "Нет данных");
}

function mapSignal(signal: ApiDecisionSignal | null | undefined): DecisionEngineAction | null {
  if (!signal) {
    return null;
  }
  return {
    id: sanitizeUserText(signal.id, "decision-signal"),
    type: sanitizeUserText(signal.type, "WATCH"),
    label: sanitizeUserText(signal.label, "Действие"),
    title: sanitizeUserText(signal.title, "Управленческий сигнал"),
    message: localizeKnownText(signal.message, "Подробности появятся после обновления данных."),
    severity: sanitizeUserText(signal.severity, "medium"),
    priority: sanitizeUserText(signal.priority, "medium"),
    expectedImpact: sanitizeUserText(signal.expectedImpact, "medium"),
    confidence: formatConfidence(signal.confidence),
    reason: localizeKnownText(signal.reason, "Причина сигнала появится после обновления данных."),
    action: localizeKnownText(signal.action, "Откройте соответствующий раздел для проверки."),
    source: sanitizeUserText(signal.source, "decision_engine"),
    tone: statusToTone(signal.severity)
  };
}

function mapChange(
  change: NonNullable<ApiDecisionEngineResponse["whatChanged"]>[number],
  index: number
): DecisionEngineChange {
  return {
    id: sanitizeUserText(change.id, `decision-change-${index + 1}`),
    type: sanitizeUserText(change.type, "signal"),
    title: localizeKnownText(change.title, "Изменение показателей"),
    message: localizeKnownText(change.message, "Подробности появятся после обновления данных."),
    severity: sanitizeUserText(change.severity, "low"),
    confidence: formatConfidence(change.confidence),
    source: sanitizeUserText(change.source, "decision_engine"),
    tone: statusToTone(change.severity)
  };
}

function mapEvidence(
  item: NonNullable<ApiDecisionEngineResponse["evidence"]>[number]
): DecisionEngineEvidence {
  return {
    label: localizeKnownText(item.label, "Фактор"),
    metric: sanitizeUserText(item.metric, "Показатель"),
    value: formatMetricValue(item.value),
    source: sanitizeUserText(item.source, "decision_engine"),
    confidence: formatConfidence(item.confidence),
    reason: localizeKnownText(item.reason, "Источник обновится после очередной синхронизации.")
  };
}

function mapForecast(forecast?: ApiDecisionEngineResponse["forecast"]): DecisionEngineForecast {
  return {
    status: sanitizeUserText(forecast?.status, "unknown"),
    message: localizeKnownText(forecast?.message, "Прогноз появится после загрузки достаточного объема данных."),
    profit: formatMetricValue(forecast?.profit),
    profitDirection: sanitizeUserText(forecast?.profitDirection, "unknown"),
    riskLevel: sanitizeUserText(forecast?.riskLevel, "unknown"),
    expectedImpact: sanitizeUserText(forecast?.expectedImpact, "unknown"),
    confidence: formatConfidence(forecast?.confidence)
  };
}

export function isApiDecisionEngineResponse(value: unknown): value is ApiDecisionEngineResponse {
  return isObject(value);
}

export function mapDecisionEngineApiResponse(payload: ApiDecisionEngineResponse): DecisionEngineSnapshot {
  const tone = statusToTone(payload.summary?.status);
  return {
    title: sanitizeUserText(payload.summary?.title, "AI Director"),
    status: localizeStatus(payload.summary?.status ?? "UNKNOWN"),
    code: sanitizeUserText(payload.summary?.code, "unknown"),
    message: localizeKnownText(
      payload.summary?.message,
      "Данные для управленческого вывода появятся после первой синхронизации."
    ),
    confidence: formatConfidence(payload.summary?.confidence),
    tone,
    mainRisk: mapSignal(payload.mainRisk),
    mainOpportunity: mapSignal(payload.mainOpportunity),
    todayActions: (payload.todayActions ?? []).map((item) => mapSignal(item)).filter(Boolean) as DecisionEngineAction[],
    whatChanged: (payload.whatChanged ?? []).map(mapChange),
    forecast: mapForecast(payload.forecast),
    evidence: (payload.evidence ?? []).map(mapEvidence),
    sources: sanitizeUserTextList(payload.sources, "")
  };
}

export async function fetchDecisionEngineApiSnapshot(signal?: AbortSignal): Promise<DecisionEngineSnapshot> {
  const payload = await requestJson<unknown>(apiEndpoints.decisionEngine, { signal });

  if (!isApiDecisionEngineResponse(payload)) {
    throw new ApiError("Parsed JSON does not match expected decision-engine schema", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.decisionEngine
    });
  }

  return mapDecisionEngineApiResponse(payload);
}
