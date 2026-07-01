import { formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { formatOptionalValue } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryHealth } from "@/features/inventory/types";

export function InventoryHealthWidget({
  health,
  loading = false,
  error = null
}: {
  health: InventoryHealth;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: health.inventoryHealth, tone: "watch" }}
      subtitle="Ключевые показатели склада"
      title="Состояние остатков"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Покрытие</div>
          <div className="mt-2 text-lg font-semibold">
            {health.coverage === null ? "Нет данных" : formatPercent(health.coverage, 0)}
          </div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Надежность прогноза</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(health.forecastConfidence, "Нет данных")}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Критичные SKU</div>
          <div className="mt-2 text-lg font-semibold">{health.criticalStock ?? "Нет данных"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">SKU с низким запасом</div>
          <div className="mt-2 text-lg font-semibold">{health.lowStock ?? "Нет данных"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 sm:col-span-2">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Статус складов</div>
          <div className="mt-2 text-lg font-semibold">{health.warehouseStatus}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={health.inventoryHealth} />
        <StatusBadge tone="risk">Критичных SKU: {health.criticalStock ?? "Нет данных"}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
