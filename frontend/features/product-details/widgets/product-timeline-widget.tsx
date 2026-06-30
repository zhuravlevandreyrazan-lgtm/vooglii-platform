import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductTimeline } from "@/features/product-details/types";

export function ProductDetailsTimelineWidget({
  timeline,
  loading = false,
  error = null
}: {
  timeline: ProductTimeline[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Timeline" title="Latest changes">
      <div className="space-y-4">
        {timeline.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <div className="flex flex-wrap items-center gap-3">
              <SeverityBadge severity={item.severity} />
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                {item.period}
              </span>
            </div>
            <p className="mt-3 text-sm font-semibold">{item.title}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
