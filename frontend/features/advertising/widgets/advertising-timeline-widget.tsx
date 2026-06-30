import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingTimelineEvent } from "@/features/advertising/types";

function periodLabel(period: AdvertisingTimelineEvent["period"]) {
  switch (period) {
    case "sync":
      return "Latest sync";
    case "analytics":
      return "Latest analytics";
    case "import":
      return "Latest import";
    default:
      return "Latest Ads Health";
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
      emptyMessage="Advertising timeline entries will appear here when backend sync events are available."
      error={error}
      loading={loading}
      subtitle="Recent advertising events"
      title="Advertising Timeline"
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
