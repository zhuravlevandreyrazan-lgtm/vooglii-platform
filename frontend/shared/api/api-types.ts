export type ApiRequestJsonOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  headers?: HeadersInit;
  body?: BodyInit | null;
  signal?: AbortSignal;
  timeoutMs?: number;
  cache?: RequestCache;
};

export type ApiErrorCode =
  | "http_error"
  | "network_error"
  | "timeout"
  | "invalid_json"
  | "invalid_shape"
  | "aborted";

export type ApiResponseMeta = {
  url: string;
  status: number | null;
  code: ApiErrorCode;
};

export type ApiRuntimeSource = "live" | "cache" | "stale_cache" | "degraded" | "fallback" | "demo" | "dev";

export type ApiRuntimeMetadata = {
  duration_ms?: number;
  cached?: boolean;
  stale?: boolean;
  degraded?: boolean;
  source?: ApiRuntimeSource | string;
};

export type WorkspaceValidationStatus = "ok" | "fallback" | "invalid";

export type WorkspaceDiagnostics = {
  source: ApiRuntimeSource;
  degraded: boolean;
  cached: boolean;
  stale: boolean;
  durationMs?: number;
  validationStatus: WorkspaceValidationStatus;
};

export type WorkspaceContext = {
  organizationId: string | null;
  cabinetId: string | null;
  mode: "live" | "demo" | "dev";
};

export type JsonObject = Record<string, unknown>;
