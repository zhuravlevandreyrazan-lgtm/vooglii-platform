import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  getArrayField,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";
import type {
  AdvisorQueryContext,
  AdvisorQueryEvidence,
  AdvisorQueryLink,
  AdvisorQueryRecommendation,
  AdvisorQueryRelated,
  AdvisorQueryResponse
} from "@/features/advisor/types";

type RawAdvisorQueryResponse = {
  status?: "ok" | "degraded" | "error";
  answer?: string;
  summary?: string;
  recommendations?: AdvisorQueryRecommendation[];
  evidence?: AdvisorQueryEvidence[];
  links?: AdvisorQueryLink[];
  related?: AdvisorQueryRelated[];
  confidence?: number;
};

function isRawAdvisorQueryResponse(value: unknown): value is RawAdvisorQueryResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    (record.status === undefined ||
      record.status === "ok" ||
      record.status === "degraded" ||
      record.status === "error") &&
    (record.answer === undefined || typeof record.answer === "string") &&
    (record.summary === undefined || typeof record.summary === "string") &&
    (record.recommendations === undefined || Array.isArray(record.recommendations)) &&
    (record.evidence === undefined || Array.isArray(record.evidence)) &&
    (record.links === undefined || Array.isArray(record.links)) &&
    (record.related === undefined || Array.isArray(record.related)) &&
    (record.confidence === undefined || typeof record.confidence === "number")
  );
}

export async function sendAdvisorQuery(
  message: string,
  context?: AdvisorQueryContext,
  signal?: AbortSignal
) {
  const payload = await requestJson<unknown>(apiEndpoints.advisorQuery, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message,
      context: context && Object.keys(context).length > 0 ? context : undefined
    }),
    signal
  });
  const record = assertWorkspacePayload(payload, apiEndpoints.advisorQuery, "Advisor query");

  if (!isRawAdvisorQueryResponse(record)) {
    throw new ApiError("Advisor query API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.advisorQuery
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  const normalized: AdvisorQueryResponse = {
    status: record.status ?? "error",
    answer: typeof record.answer === "string" ? record.answer : "No advisor answer was returned.",
    summary: typeof record.summary === "string" ? record.summary : "No advisor summary was returned.",
    recommendations: getArrayField(record, "recommendations"),
    evidence: getArrayField(record, "evidence"),
    links: getArrayField(record, "links"),
    related: getArrayField(record, "related"),
    confidence: typeof record.confidence === "number" ? record.confidence : 0,
    diagnostics: buildWorkspaceDiagnostics({
      runtime,
      validationStatus: record.status === "error" ? "invalid" : "ok",
      source: record.status === "degraded" ? "degraded" : undefined
    })
  };

  return normalized;
}
