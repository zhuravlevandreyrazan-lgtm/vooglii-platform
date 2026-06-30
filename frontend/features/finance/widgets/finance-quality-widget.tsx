import { formatPercent } from "@/features/command-center/formatters";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { FinanceQuality } from "@/features/finance/types";

export function FinanceQualityWidget({
  quality,
  loading = false,
  error = null
}: {
  quality: FinanceQuality;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: quality.health, tone: "watch" }}
      subtitle="Data Quality"
      title="Finance Quality"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Coverage</div>
          <div className="mt-2 text-lg font-semibold">{quality.coverage === null ? "n/a" : formatPercent(quality.coverage, 0)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Residual Usage</div>
          <div className="mt-2 text-lg font-semibold">{quality.residualUsage}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusBadge tone="risk">Trust {quality.trustScore ?? "n/a"}</StatusBadge>
        <StatusBadge tone="watch">{quality.confidence}</StatusBadge>
        <StatusBadge tone="neutral">{quality.health}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
