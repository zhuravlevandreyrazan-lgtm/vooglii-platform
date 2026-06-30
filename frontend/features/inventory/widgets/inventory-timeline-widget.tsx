import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryTimeline } from "@/features/inventory/types";

function periodLabel(period: InventoryTimeline["period"]) {
  switch (period) {
    case "import":
      return "Latest import";
    case "forecast":
      return "Latest forecast";
    case "restock":
      return "Latest restock plan";
    default:
      return "Latest sync";
  }
}

export function InventoryTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: InventoryTimeline[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={timeline.length === 0}
      emptyMessage="Inventory timeline entries will appear here when backend returns inventory events."
      error={error}
      loading={loading}
      subtitle="Recent inventory events"
      title="Inventory Timeline"
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
