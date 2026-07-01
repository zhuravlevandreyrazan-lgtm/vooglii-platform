import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AutomationTimelineItem } from "@/features/automation/types";

export function AutomationTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: AutomationTimelineItem[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={timeline.length === 0}
      emptyMessage="События автоматизации появятся после загрузки истории экспортов и расписаний."
      error={error}
      loading={loading}
      subtitle="Последние события"
      title="Лента автоматизации"
    >
      <div className="space-y-3">
        {timeline.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-base font-semibold">{item.title}</p>
              <SeverityBadge severity={item.severity} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
