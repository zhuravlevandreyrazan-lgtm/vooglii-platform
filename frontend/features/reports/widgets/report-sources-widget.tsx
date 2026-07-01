import { StatusBadge } from "@/shared/status";
import { formatOptionalValue, localizeStatus, localizeWorkspaceLabel } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { ReportSource } from "@/features/reports/types";

export function ReportSourcesWidget({
  sources,
  loading = false,
  error = null
}: {
  sources: ReportSource[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={sources.length === 0}
      emptyMessage="Источники отчетов появятся здесь, когда backend вернет метаданные по состоянию модулей."
      error={error}
      loading={loading}
      subtitle="Источники отчетов"
      title="Источники данных"
    >
      <div className="space-y-3">
        {sources.map((item) => (
          <div key={item.module} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{localizeWorkspaceLabel(item.module)}</div>
              <StatusBadge tone="neutral">{localizeStatus(item.status)}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="watch">{localizeStatus(item.health)}</StatusBadge>
              <StatusBadge tone="accent">{formatOptionalValue(item.lastUpdated)}</StatusBadge>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
