import { StatusBadge } from "@/shared/status";
import { formatOptionalValue, localizeStatus, localizeWorkspaceLabel } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorSource } from "@/features/advisor/types";

export function AdvisorSourcesWidget({
  sources,
  loading = false,
  error = null
}: {
  sources: AdvisorSource[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={sources.length === 0}
      emptyMessage="Статусы модулей появятся после синхронизации данных."
      error={error}
      loading={loading}
      subtitle="Состояние разделов"
      title="Доступность данных"
    >
      <div className="space-y-3">
        {sources.map((source) => (
          <div key={source.module} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{localizeWorkspaceLabel(source.module)}</div>
              <StatusBadge tone="neutral">{localizeStatus(source.status)}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="watch">{localizeStatus(source.health)}</StatusBadge>
              <StatusBadge tone="neutral">{formatOptionalValue(source.lastUpdated)}</StatusBadge>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
