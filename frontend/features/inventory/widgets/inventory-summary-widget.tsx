import { formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
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
      subtitle="Inventory Summary"
      title="Inventory Summary"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Total Stock</div>
          <div className="mt-2 text-lg font-semibold">{summary.totalStock ?? "n/a"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Critical SKU</div>
          <div className="mt-2 text-lg font-semibold">{summary.criticalSku ?? "n/a"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Days Left Avg</div>
          <div className="mt-2 text-lg font-semibold">{summary.daysLeftAverage ?? "n/a"}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Forecast Coverage</div>
          <div className="mt-2 text-lg font-semibold">
            {summary.forecastCoverage === null ? "n/a" : formatPercent(summary.forecastCoverage, 0)}
          </div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Inventory Health</div>
          <div className="mt-2 text-lg font-semibold">{summary.inventoryHealth}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Warehouse Count</div>
          <div className="mt-2 text-lg font-semibold">{summary.warehouseCount ?? "n/a"}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={summary.inventoryHealth} />
        <StatusBadge tone="risk">Critical {summary.criticalSku ?? "n/a"}</StatusBadge>
        <StatusBadge tone="accent">Warehouses {summary.warehouseCount ?? "n/a"}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
