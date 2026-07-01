import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingTimelineEvent } from "@/features/advertising/types";

function periodLabel(period: AdvertisingTimelineEvent["period"]) {
  switch (period) {
    case "sync":
      return "Последняя синхронизация";
    case "analytics":
      return "Последняя аналитика";
    case "import":
      return "Последняя загрузка";
    default:
      return "Последнее состояние рекламы";
  }
}

export function AdvertisingTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: AdvertisingTimelineEvent[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={timeline.length === 0}
      emptyMessage="События по рекламе появятся после загрузки синхронизации и аналитики."
      error={error}
      loading={loading}
      subtitle="Последние события по рекламе"
      title="Лента рекламы"
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
              <SeverityBadge severity={item.severity} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
