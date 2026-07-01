import { StatusBadge } from "@/shared/status";
import type { WorkspaceDiagnostics } from "@/shared/api/api-types";
import { localizeDiagnosticsLabel } from "@/shared/ui/status-labels";

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
  if (!diagnostics) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge tone={toneForSource(diagnostics.source)}>
        {localizeDiagnosticsLabel(diagnostics)}
      </StatusBadge>
      {context?.organization ? <StatusBadge tone="neutral">{context.organization}</StatusBadge> : null}
      {context?.cabinet ? <StatusBadge tone="neutral">{context.cabinet}</StatusBadge> : null}
      {context?.mode === "demo" ? <StatusBadge tone="accent">Демо-режим</StatusBadge> : null}
    </div>
  );
}
