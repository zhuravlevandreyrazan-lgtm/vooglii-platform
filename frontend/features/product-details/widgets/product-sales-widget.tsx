import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { WidgetCard } from "@/shared/widgets";
import type { ProductSales } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("en-US")}` : "n/a";
}

function formatNumber(value: number | null) {
  return typeof value === "number" ? value.toLocaleString("en-US") : "n/a";
}

export function ProductSalesWidget({
  sales,
  loading = false,
  error = null
}: {
  sales: ProductSales;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Sales" title="Performance">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Revenue" value={formatMoney(sales.revenue)} />
        <ProductDetailMetric label="Orders" value={formatNumber(sales.orders)} />
        <ProductDetailMetric label="Units" value={formatNumber(sales.units)} />
        <ProductDetailMetric label="Average price" value={formatMoney(sales.averagePrice)} />
        <div className="sm:col-span-2">
          <ProductDetailMetric label="Trend" value={sales.trend} hint="Backend-supplied trend summary." />
        </div>
      </div>
    </WidgetCard>
  );
}
