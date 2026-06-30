import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingHealth } from "@/features/advertising/types";

export function AdvertisingHealthWidget({
  health,
  loading = false,
  error = null
}: {
  health: AdvertisingHealth;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: health.status, tone: "watch" }}
      subtitle="Ads Health"
      title="Ads Health Panel"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Linkability</div>
          <div className="mt-2 text-lg font-semibold">{health.linkability === null ? "n/a" : formatPercent(health.linkability, 0)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Duplicate Spend</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(health.duplicateSpend)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Linked %</div>
          <div className="mt-2 text-lg font-semibold">{health.linkedPercent === null ? "n/a" : formatPercent(health.linkedPercent, 0)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Coverage</div>
          <div className="mt-2 text-lg font-semibold">{health.coverage === null ? "n/a" : formatPercent(health.coverage, 0)}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={health.adsHealth} />
        <StatusBadge tone="neutral">{health.status}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
