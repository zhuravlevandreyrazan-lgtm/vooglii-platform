import { formatCurrency } from "@/features/command-center/formatters";
import { SimpleTrend } from "@/shared/charts/simple-trend";
import { WidgetCard } from "@/shared/widgets";
import type { ProductHistory } from "@/features/products/types";

function periodLabel(period: ProductHistory["period"]) {
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

export function ProductHistoryWidget({
  history,
  loading = false,
  error = null
}: {
  history: ProductHistory[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={history.length === 0}
      emptyMessage="История по товару появится здесь после загрузки накопленной аналитики."
      error={error}
      loading={loading}
      subtitle="Historical section"
      title="Historical Performance"
    >
      <SimpleTrend
        className="mb-4"
        points={history.map((item) => ({
          label: periodLabel(item.period),
          value: item.sales ?? 0
        }))}
      />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {history.map((item) => (
          <div key={item.period} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              {periodLabel(item.period)}
            </div>
            <div className="mt-3 text-sm font-semibold">Sales {formatCurrency(item.sales)}</div>
            <div className="mt-2 text-sm font-semibold">Advertising {formatCurrency(item.advertising)}</div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.note}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
