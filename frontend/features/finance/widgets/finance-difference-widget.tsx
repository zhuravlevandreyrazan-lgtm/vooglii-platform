import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { WidgetCard } from "@/shared/widgets";
import type { FinanceDifference } from "@/features/finance/types";

export function FinanceDifferenceWidget({
  difference,
  loading = false,
  error = null
}: {
  difference: FinanceDifference;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: "Difference", tone: "watch" }}
      subtitle="Difference Panel"
      title="Finance Difference"
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Operating Profit</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(difference.operatingProfit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Official Profit</div>
          <div className="mt-2 text-lg font-semibold">
            {difference.officialProfit === null ? "Unavailable" : formatCurrency(difference.officialProfit)}
          </div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Difference</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(difference.difference)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Difference %</div>
          <div className="mt-2 text-lg font-semibold">
            {difference.differencePercent === null ? "n/a" : formatPercent(difference.differencePercent)}
          </div>
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-[var(--ink-soft)]">{difference.explanation ?? difference.reason}</p>
    </WidgetCard>
  );
}
