import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { localizeStatus } from "@/shared/ui/status-labels";
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
      subtitle="Состояние рекламы"
      title="Панель Ads Health"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Связываемость</div>
          <div className="mt-2 text-lg font-semibold">{health.linkability === null ? "Нет данных" : formatPercent(health.linkability, 0)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Дублирующийся расход</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(health.duplicateSpend)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Связанный процент</div>
          <div className="mt-2 text-lg font-semibold">{health.linkedPercent === null ? "Нет данных" : formatPercent(health.linkedPercent, 0)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Покрытие</div>
          <div className="mt-2 text-lg font-semibold">{health.coverage === null ? "Нет данных" : formatPercent(health.coverage, 0)}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={health.adsHealth} />
        <StatusBadge tone="neutral">{localizeStatus(health.status)}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
