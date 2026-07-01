import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { WidgetCard } from "@/shared/widgets";
import type { ProductFinance } from "@/features/product-details/types";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("ru-RU")}` : "Нет данных";
}

function formatPercent(value: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "Нет данных";
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
    <WidgetCard error={error} loading={loading} subtitle="Финансы" title="Прибыльность">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Прибыль" value={formatMoney(finance.profit)} />
        <ProductDetailMetric label="Маржинальность" value={formatPercent(finance.margin)} />
        <ProductDetailMetric label="Расходы" value={formatMoney(finance.expenses)} />
        <ProductDetailMetric label="Официальная прибыль" value={formatMoney(finance.officialProfit)} />
        <div className="sm:col-span-2">
          <ProductDetailMetric
            label="Расхождение"
            value={formatMoney(finance.difference)}
            hint="Расхождение появится после полной финансовой сверки."
          />
        </div>
      </div>
    </WidgetCard>
  );
}
