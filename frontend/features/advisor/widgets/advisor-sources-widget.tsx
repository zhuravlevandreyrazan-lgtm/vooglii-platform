import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorSource } from "@/features/advisor/types";

export function AdvisorSourcesWidget({
  sources,
  loading = false,
  error = null
}: {
  sources: AdvisorSource[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={sources.length === 0}
      emptyMessage="Advisor source health will appear here when module source payloads are available."
      error={error}
      loading={loading}
      subtitle="Workspace sources"
      title="Advisor Sources"
    >
      <div className="space-y-3">
        {sources.map((source) => (
          <div key={source.module} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{source.module}</div>
              <StatusBadge tone="neutral">{source.status}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="watch">{source.health}</StatusBadge>
              <StatusBadge tone="accent">{source.source}</StatusBadge>
              <StatusBadge tone="neutral">{source.lastUpdated ?? "n/a"}</StatusBadge>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
