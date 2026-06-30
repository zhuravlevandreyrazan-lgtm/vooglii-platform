import { WidgetCard } from "@/shared/widgets";
import type { ProductHistory } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("en-US")}` : "n/a";
}

function formatPeriod(period: ProductHistory["period"]) {
  switch (period) {
    case "today":
      return "Today";
    case "sevenDays":
      return "7 Days";
    case "thirtyDays":
      return "30 Days";
    case "ninetyDays":
      return "90 Days";
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
    <WidgetCard error={error} loading={loading} subtitle="History" title="Performance windows">
      <div className="grid gap-4 lg:grid-cols-2">
        {history.map((item) => (
          <div key={item.period} className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <p className="text-sm font-semibold">{formatPeriod(item.period)}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Revenue
                </p>
                <p className="mt-2 text-sm">{formatMoney(item.revenue)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Profit
                </p>
                <p className="mt-2 text-sm">{formatMoney(item.profit)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Orders
                </p>
                <p className="mt-2 text-sm">
                  {typeof item.orders === "number" ? item.orders.toLocaleString("en-US") : "n/a"}
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
