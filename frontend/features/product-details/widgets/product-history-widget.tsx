import { WidgetCard } from "@/shared/widgets";
import type { ProductHistory } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `в‚Ѕ${value.toLocaleString("en-US")}` : "Нет данных";
}

function formatPeriod(period: ProductHistory["period"]) {
  switch (period) {
    case "today":
      return "Сегодня";
    case "sevenDays":
      return "7 дней";
    case "thirtyDays":
      return "30 дней";
    case "ninetyDays":
      return "90 дней";
    default:
      return period;
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
    <WidgetCard error={error} loading={loading} subtitle="История" title="Показатели по периодам">
      <div className="grid gap-4 lg:grid-cols-2">
        {history.map((item) => (
          <div key={item.period} className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <p className="text-sm font-semibold">{formatPeriod(item.period)}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Выручка
                </p>
                <p className="mt-2 text-sm">{formatMoney(item.revenue)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Прибыль
                </p>
                <p className="mt-2 text-sm">{formatMoney(item.profit)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Заказы
                </p>
                <p className="mt-2 text-sm">
                  {typeof item.orders === "number" ? item.orders.toLocaleString("en-US") : "Нет данных"}
                </p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-6 text-[var(--ink-soft)]">{item.note}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
