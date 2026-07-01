import { SeverityBadge } from "@/shared/status";
import { localizeWorkspaceLabel } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { ProductAlert } from "@/features/products/types";

export function ProductAlertsWidget({
  alerts,
  loading = false,
  error = null
}: {
  alerts: ProductAlert[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={alerts.length === 0}
      emptyMessage="Сигналы по товарам появятся здесь, когда backend вернет предупреждения по SKU."
      error={error}
      loading={loading}
      subtitle="Сигналы backend"
      title="Сигналы по товарам"
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
              Источник: {localizeWorkspaceLabel(alert.source)}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
