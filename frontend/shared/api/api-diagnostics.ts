import { ApiError } from "@/shared/api/api-error";
import { getApiBaseUrl, resolveApiUrl } from "@/shared/api/api-client";

export type ApiIntegrationStatus =
  | "backend_configured"
  | "backend_unreachable"
  | "endpoint_failed"
  | "using_fallback";

export type ApiIntegrationDiagnostic = {
  endpoint: string;
  configured: boolean;
  status: ApiIntegrationStatus;
  usingFallback: boolean;
  requestUrl: string;
  message: string;
};

export function getApiIntegrationDiagnostic({
  endpoint,
  error,
  usingFallback
}: {
  endpoint: string;
  error?: unknown;
  usingFallback: boolean;
}): ApiIntegrationDiagnostic {
  const configured = Boolean(getApiBaseUrl());
  const requestUrl = resolveApiUrl(endpoint);

  if (usingFallback) {
    return {
      endpoint,
      configured,
      status: "using_fallback",
      usingFallback: true,
      requestUrl,
      message: "Используются резервные данные."
    };
  }

  if (error instanceof ApiError) {
    return {
      endpoint,
      configured,
      status: error.code === "network_error" || error.code === "timeout"
        ? "backend_unreachable"
        : "endpoint_failed",
      usingFallback: false,
      requestUrl,
      message: error.message
    };
  }

  return {
    endpoint,
    configured,
    status: "backend_configured",
    usingFallback: false,
    requestUrl,
    message: configured
      ? "Базовый URL API настроен."
      : "Используются относительные API-маршруты через локальный прокси."
  };
}
