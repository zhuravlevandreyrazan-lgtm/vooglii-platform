export { ApiError, formatApiErrorMessage } from "@/shared/api/api-error";
export { getApiIntegrationDiagnostic } from "@/shared/api/api-diagnostics";
export { RuntimeBadge } from "@/shared/api/runtime-badge";
export type {
  ApiIntegrationDiagnostic,
  ApiIntegrationStatus
} from "@/shared/api/api-diagnostics";
export { getApiBaseUrl, normalizeApiBaseUrl, requestJson, resolveApiUrl } from "@/shared/api/api-client";
export { apiEndpoints } from "@/shared/api/endpoints";
export type { ApiEndpointName } from "@/shared/api/endpoints";
export {
  FALLBACK_DATA_MESSAGE,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  getArrayField,
  getObjectField,
  isRecord,
  normalizeRuntimeMetadata
} from "@/shared/api/workspace-data";
export type {
  ApiErrorCode,
  ApiRequestJsonOptions,
  ApiResponseMeta,
  ApiRuntimeMetadata,
  ApiRuntimeSource,
  JsonObject,
  WorkspaceContext,
  WorkspaceDiagnostics,
  WorkspaceValidationStatus
} from "@/shared/api/api-types";
