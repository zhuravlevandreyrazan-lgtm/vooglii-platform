import { SeverityBadge } from "@/shared/status";
import { localizeKnownText, localizeSourceName } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { FinanceAlert } from "@/features/finance/types";

export function FinanceAlertsWidget({
  alerts,
  loading = false,
  error = null
}: {
  alerts: FinanceAlert[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={alerts.length === 0}
      emptyMessage="Финансовые предупреждения появятся здесь после получения актуальных сигналов."
      error={error}
      loading={loading}
      subtitle="Сигналы и предупреждения"
      title="Финансовые сигналы"
    >
      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{localizeKnownText(alert.title, "Сигнал")}</div>
              <SeverityBadge severity={alert.severity} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
              {localizeKnownText(alert.description, "Подробности появятся после обновления данных.")}
            </p>
            <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              Источник: {localizeSourceName(alert.source)}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
