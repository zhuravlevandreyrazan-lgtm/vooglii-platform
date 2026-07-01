import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryAlert } from "@/features/inventory/types";

export function InventoryAlertsWidget({
  alerts,
  loading = false,
  error = null
}: {
  alerts: InventoryAlert[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={alerts.length === 0}
      emptyMessage="Сигналы по остаткам появятся после получения предупреждений от backend."
      error={error}
      loading={loading}
      subtitle="Сигналы по остаткам"
      title="Предупреждения"
    >
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{alert.title}</div>
              <SeverityBadge severity={alert.severity} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{alert.description}</p>
            <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              Источник: {alert.source}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
