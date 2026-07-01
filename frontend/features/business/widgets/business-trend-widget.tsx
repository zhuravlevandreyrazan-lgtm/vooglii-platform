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
      title="Период"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выручка</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(trend.revenue)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Прибыль</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(trend.profit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Маржинальность</div>
          <div className="mt-2 text-lg font-semibold">{formatPercent(trend.margin)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Заказы</div>
          <div className="mt-2 text-lg font-semibold">{trend.orders.toLocaleString("en-US")}</div>
        </div>
      </div>
      <SimpleTrend
        className="mt-4"
        points={[
          { label: "Выручка", value: trend.revenue },
          { label: "Прибыль", value: trend.profit },
          { label: "Заказы", value: trend.orders },
          { label: "Единицы", value: trend.unitsSold }
        ]}
      />
    </WidgetCard>
  );
}
