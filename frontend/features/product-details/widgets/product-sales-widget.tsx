import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import type { ProductSales } from "@/features/product-details/types";
import { formatOptionalValue } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("ru-RU")}` : "Нет данных";
}

function formatNumber(value: number | null) {
  return typeof value === "number" ? value.toLocaleString("ru-RU") : "Нет данных";
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
    <WidgetCard error={error} loading={loading} subtitle="Продажи" title="Результаты SKU">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Выручка" value={formatMoney(sales.revenue)} />
        <ProductDetailMetric label="Заказы" value={formatNumber(sales.orders)} />
        <ProductDetailMetric label="Штуки" value={formatNumber(sales.units)} />
        <ProductDetailMetric label="Средняя цена" value={formatMoney(sales.averagePrice)} />
        <div className="sm:col-span-2">
          <ProductDetailMetric
            label="Динамика"
            value={formatOptionalValue(sales.trend)}
            hint="Краткая оценка тренда по товару."
          />
        </div>
      </div>
    </WidgetCard>
  );
}
