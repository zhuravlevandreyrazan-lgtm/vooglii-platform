import { formatCurrency } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { FinanceSummary } from "@/features/finance/types";

export function FinanceSummaryWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: FinanceSummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: summary.status, tone: "watch" }}
      subtitle="Finance Summary"
      title="Finance Summary"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Operating Profit</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.operatingProfit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Official Profit</div>
          <div className="mt-2 text-lg font-semibold">{summary.officialProfit === null ? "Unavailable" : formatCurrency(summary.officialProfit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Difference</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.difference)}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={summary.health} score={summary.trustScore ?? undefined} />
        <StatusBadge tone="risk">Trust {summary.trustScore ?? "n/a"}</StatusBadge>
        <StatusBadge tone="neutral">{summary.status}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
