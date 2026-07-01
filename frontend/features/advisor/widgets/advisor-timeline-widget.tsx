import { SeverityBadge } from "@/shared/status";
import { localizeWorkspaceLabel } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorTimeline } from "@/features/advisor/types";

export function AdvisorTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: AdvisorTimeline[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={timeline.length === 0}
      emptyMessage="События советника появятся здесь, когда backend начнет возвращать журнал изменений."
      error={error}
      loading={loading}
      subtitle="Последние события"
      title="Лента советника"
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
              Источник: {localizeWorkspaceLabel(item.source)}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
