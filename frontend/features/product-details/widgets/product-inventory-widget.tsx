import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { WidgetCard } from "@/shared/widgets";
import type { ProductInventory } from "@/features/product-details/types";

function formatNumber(value: number | null) {
  return typeof value === "number" ? value.toLocaleString("en-US") : "Нет данных";
}

export function ProductInventoryWidget({
  inventory,
  loading = false,
  error = null
}: {
  inventory: ProductInventory;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Остатки" title="Наличие">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Остаток" value={formatNumber(inventory.stock)} />
        <ProductDetailMetric label="Резерв" value={formatNumber(inventory.reserved)} />
        <ProductDetailMetric label="Доступно" value={formatNumber(inventory.available)} />
        <ProductDetailMetric
          label="Дней запаса"
          value={typeof inventory.daysLeft === "number" ? `${inventory.daysLeft} дней` : "Нет данных"}
        />
        <ProductDetailMetric label="Склад" value={inventory.warehouse} />
        <ProductDetailMetric label="Прогноз" value={inventory.forecast} />
      </div>
    </WidgetCard>
  );
}
