import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ReportTimeline } from "@/features/reports/types";

export function ReportTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: ReportTimeline[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={timeline.length === 0}
      emptyMessage="Reports timeline will appear here when backend returns report timeline entries."
      error={error}
      loading={loading}
      subtitle="Reports timeline"
      title="Reports Timeline"
    >
      <div className="space-y-3">
        {timeline.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{item.title}</div>
              <SeverityBadge severity={item.severity} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
            <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              Source {item.source}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
