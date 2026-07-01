import { WidgetCard } from "@/shared/widgets";
import type { KpiOpportunity, KpiRisk } from "@/features/command-center/kpi-types";
import { localizeKnownText, localizeSourceName, localizeStatus } from "@/shared/ui/status-labels";

export type RiskOpportunityPanelProps = {
  topRisk: KpiRisk | null;
  topOpportunity: KpiOpportunity | null;
  loading?: boolean;
  error?: string | null;
};

function CompactSignalCard({
  title,
  emptyMessage,
  item,
  loading = false,
  error = null
}: {
  title: string;
  emptyMessage: string;
  item: KpiRisk | KpiOpportunity | null;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={!item}
      emptyMessage={emptyMessage}
      error={error}
      loading={loading}
      status={item ? { label: localizeStatus(item.tone), tone: item.tone } : undefined}
      subtitle={item ? item.title : "Сигнал появится после синхронизации"}
      title={title}
    >
      {item ? (
        <div className="space-y-3">
          <p className="text-sm leading-6 text-[var(--ink-soft)]">{item.summary}</p>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
            Основание: {localizeKnownText(localizeSourceName(item.source), "данные кабинета")}
          </div>
        </div>
      ) : null}
    </WidgetCard>
  );
}

export function RiskOpportunityPanel({
  topRisk,
  topOpportunity,
  loading = false,
  error = null
}: RiskOpportunityPanelProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <CompactSignalCard
        emptyMessage="Сейчас нет подтвержденного критичного риска."
        error={error}
        item={topRisk}
        loading={loading}
        title="Главный риск"
      />
      <CompactSignalCard
        emptyMessage="Сейчас нет подтвержденной точки роста."
        error={error}
        item={topOpportunity}
        loading={loading}
        title="Точка роста"
      />
    </div>
  );
}
