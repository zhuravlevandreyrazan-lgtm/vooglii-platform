import { StatusBadge } from "@/shared/status";
import type { WorkspaceDiagnostics } from "@/shared/api/api-types";

type RuntimeContext = {
  organization?: string | null;
  cabinet?: string | null;
  mode?: string | null;
};

function toneForSource(source: WorkspaceDiagnostics["source"]) {
  switch (source) {
    case "demo":
      return "accent";
    case "dev":
      return "neutral";
    case "live":
      return "healthy";
    case "cache":
      return "accent";
    case "stale_cache":
      return "watch";
    case "degraded":
    case "fallback":
      return "risk";
    default:
      return "neutral";
  }
}

export function RuntimeBadge({
  diagnostics,
  context
}: {
  diagnostics?: WorkspaceDiagnostics;
  context?: RuntimeContext;
}) {
  if (process.env.NODE_ENV !== "development" || !diagnostics) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge tone={toneForSource(diagnostics.source)}>
        source {diagnostics.source}
      </StatusBadge>
      {typeof diagnostics.durationMs === "number" ? (
        <StatusBadge tone="neutral">{Math.round(diagnostics.durationMs)} ms</StatusBadge>
      ) : null}
      <StatusBadge tone={diagnostics.degraded ? "watch" : "healthy"}>
        degraded {diagnostics.degraded ? "true" : "false"}
      </StatusBadge>
      {diagnostics.cached ? <StatusBadge tone="accent">cached</StatusBadge> : null}
      {diagnostics.stale ? <StatusBadge tone="watch">stale</StatusBadge> : null}
      {context?.organization ? <StatusBadge tone="neutral">{context.organization}</StatusBadge> : null}
      {context?.cabinet ? <StatusBadge tone="neutral">{context.cabinet}</StatusBadge> : null}
      {context?.mode ? <StatusBadge tone="accent">mode {context.mode}</StatusBadge> : null}
    </div>
  );
}
