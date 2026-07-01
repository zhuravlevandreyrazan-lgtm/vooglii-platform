import { formatPercent } from "@/features/command-center/formatters";
import { SimpleTrend } from "@/shared/charts/simple-trend";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryHistory } from "@/features/inventory/types";

function periodLabel(period: InventoryHistory["period"]) {
  switch (period) {
    case "today":
      return "Today";
    case "sevenDays":
      return "7 Days";
    case "thirtyDays":
      return "30 Days";
    default:
      return "90 Days";
  }
}

export function InventoryHistoryWidget({
  history,
  loading = false,
  error = null
}: {
  history: InventoryHistory[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={history.length === 0}
      emptyMessage="История по остаткам появится здесь после загрузки накопленных данных."
      error={error}
      loading={loading}
      subtitle="Historical inventory"
      title="Historical Inventory"
    >
      <SimpleTrend
        className="mb-4"
        points={history.map((item) => ({
          label: periodLabel(item.period),
          value: item.coverage ?? 0
        }))}
      />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {history.map((item) => (
          <div key={item.period} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              {periodLabel(item.period)}
            </div>
            <div className="mt-3 text-sm font-semibold">Stock {item.stock ?? "n/a"}</div>
            <div className="mt-2 text-sm font-semibold">
              Coverage {item.coverage === null ? "n/a" : formatPercent(item.coverage, 0)}
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.note}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
