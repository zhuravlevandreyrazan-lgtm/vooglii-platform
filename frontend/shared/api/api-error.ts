import type { ApiErrorCode, ApiResponseMeta } from "@/shared/api/api-types";

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number | null;
  readonly url: string;
  readonly cause?: unknown;

  constructor(message: string, meta: ApiResponseMeta, cause?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = meta.code;
    this.status = meta.status;
    this.url = meta.url;
    this.cause = cause;
  }
}

export function formatApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Не удалось получить ответ API.";
}
