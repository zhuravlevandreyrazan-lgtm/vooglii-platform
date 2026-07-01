import { ApiError } from "@/shared/api/api-error";
import type { ApiRequestJsonOptions } from "@/shared/api/api-types";

const DEFAULT_TIMEOUT_MS = 10000;

type RuntimeConfigWindow = Window & {
  __VOOGLII_RUNTIME_CONFIG__?: {
    NEXT_PUBLIC_API_BASE_URL?: string | null;
    NEXT_PUBLIC_APP_ENV?: string | null;
  };
};

export function normalizeApiBaseUrl(value?: string | null) {
  const text = (value ?? "").trim();
  return text ? text.replace(/\/+$/, "") : "";
}

export function getApiBaseUrl() {
  if (typeof window !== "undefined") {
    return normalizeApiBaseUrl((window as RuntimeConfigWindow).__VOOGLII_RUNTIME_CONFIG__?.NEXT_PUBLIC_API_BASE_URL);
  }

  return normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
}

export function resolveApiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseUrl = getApiBaseUrl();

  return baseUrl ? `${baseUrl}${normalizedPath}` : normalizedPath;
}

export async function requestJson<T>(path: string, options: ApiRequestJsonOptions = {}) {
  const url = resolveApiUrl(path);
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  const abortFromCaller = () => {
    controller.abort(options.signal?.reason);
  };

  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort(options.signal.reason);
    } else {
      options.signal.addEventListener("abort", abortFromCaller, { once: true });
    }
  }

  const timeoutId = window.setTimeout(() => {
    controller.abort(new DOMException("Request timed out.", "TimeoutError"));
  }, timeoutMs);

  try {
    const response = await fetch(url, {
      method: options.method ?? "GET",
      headers: options.headers,
      body: options.body,
      signal: controller.signal,
      cache: options.cache ?? "no-store"
    });

    if (!response.ok) {
      throw new ApiError(`API returned ${response.status}`, {
        code: "http_error",
        status: response.status,
        url
      });
    }

    const rawText = await response.text();

    if (!rawText.trim()) {
      return null as T;
    }

    try {
      return JSON.parse(rawText) as T;
    } catch (error) {
      throw new ApiError("API returned invalid JSON.", {
        code: "invalid_json",
        status: response.status,
        url
      }, error);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (controller.signal.aborted) {
      const isTimeout = controller.signal.reason instanceof DOMException &&
        controller.signal.reason.name === "TimeoutError";

      throw new ApiError(isTimeout ? "API request timed out." : "API request was aborted.", {
        code: isTimeout ? "timeout" : "aborted",
        status: null,
        url
      }, error);
    }

    throw new ApiError("Backend is unreachable.", {
      code: "network_error",
      status: null,
      url
    }, error);
  } finally {
    window.clearTimeout(timeoutId);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }
}
