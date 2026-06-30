import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { SimpleTrend } from "@/shared/charts/simple-trend";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingSummary } from "@/features/advertising/types";

export function AdvertisingSummaryWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: AdvertisingSummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: summary.status, tone: "watch" }}
      subtitle="Advertising Summary"
      title="Advertising Summary"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Advertising Spend</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.advertisingSpend)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Linked Spend</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.linkedSpend)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Unlinked Spend</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.unlinkedSpend)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ROAS</div>
          <div className="mt-2 text-lg font-semibold">{summary.roas === null ? "n/a" : `${summary.roas.toFixed(1)}x`}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ACOS</div>
          <div className="mt-2 text-lg font-semibold">{summary.acos === null ? "n/a" : formatPercent(summary.acos)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Ads Health</div>
          <div className="mt-2 text-lg font-semibold">{summary.adsHealth}</div>
        </div>
      </div>
      {summary.trend?.length ? <SimpleTrend className="mt-4" points={summary.trend} /> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={summary.adsHealth} />
        <StatusBadge tone="neutral">Trust {summary.trust}</StatusBadge>
        <StatusBadge tone="watch">{summary.status}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
