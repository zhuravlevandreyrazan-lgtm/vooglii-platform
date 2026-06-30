import { ApiError } from "@/shared/api/api-error";
import type {
  ApiRuntimeMetadata,
  ApiRuntimeSource,
  WorkspaceDiagnostics,
  WorkspaceValidationStatus
} from "@/shared/api/api-types";

export const FALLBACK_DATA_MESSAGE = "Using fallback data. Backend response is unavailable or invalid.";

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function getObjectField(
  value: Record<string, unknown>,
  key: string
): Record<string, unknown> | undefined {
  const field = value[key];
  return isRecord(field) ? field : undefined;
}

export function getArrayField<T>(value: Record<string, unknown>, key: string): T[] {
  const field = value[key];
  return Array.isArray(field) ? (field as T[]) : [];
}

export function assertWorkspacePayload(
  payload: unknown,
  endpoint: string,
  workspace: string
): Record<string, unknown> {
  if (!isRecord(payload)) {
    throw new ApiError(`${workspace} API payload has an invalid shape.`, {
      code: "invalid_shape",
      status: null,
      url: endpoint
    });
  }

  return payload;
}

function safeBoolean(value: unknown) {
  return typeof value === "boolean" ? value : false;
}

function safeNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function safeSource(value: unknown): ApiRuntimeSource | "live" {
  if (
    value === "live" ||
    value === "cache" ||
    value === "stale_cache" ||
    value === "degraded" ||
    value === "fallback"
  ) {
    return value;
  }

  return "live";
}

export function normalizeRuntimeMetadata(payload: Record<string, unknown>): ApiRuntimeMetadata | undefined {
  const runtime = getObjectField(payload, "runtime");
  if (!runtime) {
    return undefined;
  }

  return {
    duration_ms: safeNumber(runtime.duration_ms),
    cached: safeBoolean(runtime.cached),
    stale: safeBoolean(runtime.stale),
    degraded: safeBoolean(runtime.degraded),
    source: safeSource(runtime.source)
  };
}

export function buildWorkspaceDiagnostics({
  runtime,
  validationStatus,
  source
}: {
  runtime?: ApiRuntimeMetadata;
  validationStatus: WorkspaceValidationStatus;
  source?: ApiRuntimeSource;
}): WorkspaceDiagnostics {
  const resolvedSource = source ?? safeSource(runtime?.source);

  return {
    source: resolvedSource,
    degraded: source === "fallback" ? true : safeBoolean(runtime?.degraded),
    cached: safeBoolean(runtime?.cached),
    stale: safeBoolean(runtime?.stale),
    durationMs: safeNumber(runtime?.duration_ms),
    validationStatus
  };
}

export function createFallbackDiagnostics(): WorkspaceDiagnostics {
  return {
    source: "fallback",
    degraded: true,
    cached: false,
    stale: false,
    durationMs: undefined,
    validationStatus: "fallback"
  };
}
