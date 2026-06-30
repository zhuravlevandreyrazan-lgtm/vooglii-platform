import { formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
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
      subtitle="Inventory Health"
      title="Inventory Health"
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Coverage</div>
          <div className="mt-2 text-lg font-semibold">
            {health.coverage === null ? "n/a" : formatPercent(health.coverage, 0)}
          </div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Forecast Confidence</div>
          <div className="mt-2 text-lg font-semibold">{health.forecastConfidence}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Critical Stock</div>
          <div className="mt-2 text-lg font-semibold">{health.criticalStock ?? "n/a"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Low Stock</div>
          <div className="mt-2 text-lg font-semibold">{health.lowStock ?? "n/a"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 sm:col-span-2">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Warehouse Status</div>
          <div className="mt-2 text-lg font-semibold">{health.warehouseStatus}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={health.inventoryHealth} />
        <StatusBadge tone="risk">Critical {health.criticalStock ?? "n/a"}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
