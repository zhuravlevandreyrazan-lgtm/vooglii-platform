import { WidgetCard } from "@/shared/widgets";
import type { NotificationOverview, NotificationQuickStat } from "@/features/notifications/types";

export function NotificationsOverviewWidget({
  overview,
  quickStats,
  loading = false,
  error = null
}: {
  overview: NotificationOverview;
  quickStats: NotificationQuickStat[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Notification overview" title="Overview">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {quickStats.map((item) => (
          <div key={item.label} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold">{item.value}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-[22px] border border-[var(--line)] bg-white/70 p-4 text-sm leading-7 text-[var(--ink-soft)]">
        Last delivery: {overview.lastDelivery ?? "No delivery yet"}.
      </div>
    </WidgetCard>
  );
}
