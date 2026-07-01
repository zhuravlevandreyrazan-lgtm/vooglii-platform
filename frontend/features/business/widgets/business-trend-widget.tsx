import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import type { BusinessTrend } from "@/features/business/types";
import { SimpleTrend } from "@/shared/charts/simple-trend";
import { WidgetCard } from "@/shared/widgets";

function formatCount(value: number | null) {
  return typeof value === "number" ? value.toLocaleString("en-US") : "Нет данных";
}

function formatMargin(value: number | null) {
  return typeof value === "number" ? formatPercent(value) : "Нет данных";
}

function chartValue(value: number | null) {
  return typeof value === "number" ? value : 0;
}

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
          <div className="mt-2 text-lg font-semibold">{formatMargin(trend.margin)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Заказы</div>
          <div className="mt-2 text-lg font-semibold">{formatCount(trend.orders)}</div>
        </div>
      </div>
      <SimpleTrend
        className="mt-4"
        points={[
          { label: "Выручка", value: chartValue(trend.revenue) },
          { label: "Прибыль", value: chartValue(trend.profit) },
          { label: "Заказы", value: chartValue(trend.orders) },
          { label: "Единицы", value: chartValue(trend.unitsSold) }
        ]}
      />
    </WidgetCard>
  );
}
