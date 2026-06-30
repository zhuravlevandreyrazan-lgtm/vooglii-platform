import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { SimpleTrend } from "@/shared/charts/simple-trend";
import { WidgetCard } from "@/shared/widgets";
import type { BusinessTrend } from "@/features/business/types";

export function BusinessTrendWidget({
  trend,
  loading = false,
  error = null
}: {
  trend: BusinessTrend;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: trend.label, tone: "neutral" }}
      subtitle={trend.label}
      title="Trend Window"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Revenue</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(trend.revenue)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Profit</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(trend.profit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Margin</div>
          <div className="mt-2 text-lg font-semibold">{formatPercent(trend.margin)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Orders</div>
          <div className="mt-2 text-lg font-semibold">{trend.orders.toLocaleString("en-US")}</div>
        </div>
      </div>
      <SimpleTrend
        className="mt-4"
        points={[
          { label: "Revenue", value: trend.revenue },
          { label: "Profit", value: trend.profit },
          { label: "Orders", value: trend.orders },
          { label: "Units", value: trend.unitsSold }
        ]}
      />
    </WidgetCard>
  );
}
