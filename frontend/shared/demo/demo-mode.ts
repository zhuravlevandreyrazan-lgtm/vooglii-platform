export const DEMO_QUERY_PARAM = "demo";
export const DEMO_QUERY_VALUE = "true";
export const DEMO_STORAGE_KEY = "vooglii-demo-mode";

export function isDemoQueryEnabled(value: string | null | undefined) {
  return String(value ?? "").trim().toLowerCase() === DEMO_QUERY_VALUE;
}

export function applyDemoToSearchParams(
  searchParams: URLSearchParams,
  enabled: boolean
) {
  const next = new URLSearchParams(searchParams);
  if (enabled) {
    next.set(DEMO_QUERY_PARAM, DEMO_QUERY_VALUE);
  } else {
    next.delete(DEMO_QUERY_PARAM);
  }
  return next;
}
