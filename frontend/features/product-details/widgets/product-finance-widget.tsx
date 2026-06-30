import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { WidgetCard } from "@/shared/widgets";
import type { ProductFinance } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("en-US")}` : "n/a";
}

function formatPercent(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "n/a";
}

export function ProductFinanceWidget({
  finance,
  loading = false,
  error = null
}: {
  finance: ProductFinance;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Finance" title="Profitability">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Profit" value={formatMoney(finance.profit)} />
        <ProductDetailMetric label="Margin" value={formatPercent(finance.margin)} />
        <ProductDetailMetric label="Expenses" value={formatMoney(finance.expenses)} />
        <ProductDetailMetric label="Official profit" value={formatMoney(finance.officialProfit)} />
        <div className="sm:col-span-2">
          <ProductDetailMetric
            label="Difference"
            value={formatMoney(finance.difference)}
            hint="Difference remains placeholder until backend official-vs-management profit payload is available."
          />
        </div>
      </div>
    </WidgetCard>
  );
}
