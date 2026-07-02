import { formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { formatOptionalValue, localizeStatus } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { InventorySummary } from "@/features/inventory/types";

export function InventorySummaryWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: InventorySummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: summary.inventoryHealth, tone: "watch" }}
      subtitle="Сводка по остаткам и покрытию"
      title="Остатки"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Общий остаток</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.totalStock)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Критичных SKU</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.criticalSku)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Средний запас, дни</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.daysLeftAverage)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Покрытие прогноза</div>
          <div className="mt-2 text-lg font-semibold">
            {summary.forecastCoverage === null ? "Нет данных" : formatPercent(summary.forecastCoverage, 0)}
          </div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Состояние остатков</div>
          <div className="mt-2 text-lg font-semibold">{localizeStatus(summary.inventoryHealth)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Складов в контуре</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.warehouseCount)}</div>
        </div>
      </div>
      {summary.status ? (
        <div className="mt-4 rounded-[22px] border border-[var(--line)] bg-white/70 p-4 text-sm text-[var(--ink-soft)]">
          {summary.status}
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={summary.inventoryHealth} />
        <StatusBadge tone="risk">Критичных SKU: {formatOptionalValue(summary.criticalSku)}</StatusBadge>
        <StatusBadge tone="accent">Складов: {formatOptionalValue(summary.warehouseCount)}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
