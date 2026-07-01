import { formatSeverityLabel } from "@/features/command-center/formatters";
import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { FinanceTimelineEvent } from "@/features/finance/types";

function periodLabel(period: FinanceTimelineEvent["period"]) {
  switch (period) {
    case "latest":
      return "Последнее обновление";
    case "audit":
      return "Аудит прибыли";
    default:
      return "Синхронизация финансов";
  }
}

export function FinanceTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: FinanceTimelineEvent[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={timeline.length === 0}
      emptyMessage="События по финансам появятся здесь после синхронизации данных."
      error={error}
      loading={loading}
      subtitle="Последние события по финансам"
      title="Лента финансов"
    >
      <div className="space-y-3">
        {timeline.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.title}</div>
                <div className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  {periodLabel(item.period)}
                </div>
              </div>
              <SeverityBadge severity={formatSeverityLabel(item.severity)} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
