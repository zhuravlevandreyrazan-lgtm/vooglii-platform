import { WidgetCard } from "@/shared/widgets";
import type { ForecastSnapshot } from "@/features/forecast/types";

function formatNumber(value: number | null, suffix = "") {
  if (value === null || value === undefined) {
    return "Нет данных";
  }
  return `${Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value)}${suffix}`;
}

export function ForecastSummaryWidget({
  data,
  loading = false,
  error = null,
  updatedAt
}: {
  data: ForecastSnapshot;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string | null;
}) {
  const sevenDays = data.periods.sevenDays;
  const metrics = [
    { label: "Выручка 7 дней", value: formatNumber(sevenDays.expectedRevenue, " ₽") },
    { label: "Заказы 7 дней", value: formatNumber(sevenDays.expectedOrders) },
    { label: "Опер. прибыль", value: formatNumber(data.profitForecast.expectedOperatingProfit, " ₽") },
    { label: "Маржа", value: data.profitForecast.expectedMargin === null ? "Нет данных" : `${data.profitForecast.expectedMargin.toFixed(1)}%` }
  ];

  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: data.summary.status, tone: data.summary.status === "ready" ? "healthy" : "watch" }}
      subtitle="Горизонт 7 дней"
      title="Прогноз"
      updatedAt={updatedAt ?? undefined}
    >
      <div className="space-y-4">
        <p className="text-sm leading-6 text-[var(--ink-soft)]">{data.summary.message}</p>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-[18px] border border-[var(--line)] bg-white/72 p-3">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                {metric.label}
              </div>
              <div className="mt-2 text-lg font-semibold">{metric.value}</div>
            </div>
          ))}
        </div>
      </div>
    </WidgetCard>
  );
}
