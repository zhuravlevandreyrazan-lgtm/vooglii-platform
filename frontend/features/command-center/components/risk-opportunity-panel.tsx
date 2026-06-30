import { WidgetCard } from "@/shared/widgets";
import type { KpiOpportunity, KpiRisk } from "@/features/command-center/kpi-types";

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
      status={item ? { label: item.tone, tone: item.tone } : undefined}
      title={title}
    >
      {item ? (
        <div>
          <div className="text-base font-semibold">{item.title}</div>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.summary}</p>
          <div className="mt-4 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
            Source {item.source}
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
    <div className="grid gap-6 md:grid-cols-2">
      <CompactSignalCard
        emptyMessage="No material risk is available from the current executive signals."
        error={error}
        item={topRisk}
        loading={loading}
        title="Top Risk"
      />
      <CompactSignalCard
        emptyMessage="No confirmed growth opportunity is available from the current executive signals."
        error={error}
        item={topOpportunity}
        loading={loading}
        title="Top Opportunity"
      />
    </div>
  );
}
