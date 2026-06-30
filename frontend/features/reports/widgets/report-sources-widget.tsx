import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ReportSource } from "@/features/reports/types";

export function ReportSourcesWidget({
  sources,
  loading = false,
  error = null
}: {
  sources: ReportSource[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={sources.length === 0}
      emptyMessage="Report sources will appear here when backend returns source health metadata."
      error={error}
      loading={loading}
      subtitle="Report sources"
      title="Sources"
    >
      <div className="space-y-3">
        {sources.map((item) => (
          <div key={item.module} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{item.module}</div>
              <StatusBadge tone="neutral">{item.status}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="watch">{item.health}</StatusBadge>
              <StatusBadge tone="accent">{item.lastUpdated ?? "n/a"}</StatusBadge>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
