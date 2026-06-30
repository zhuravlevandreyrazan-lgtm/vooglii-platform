import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import { WidgetCard } from "@/shared/widgets";
import type { ProductInventory } from "@/features/product-details/types";

function formatNumber(value: number | null) {
  return typeof value === "number" ? value.toLocaleString("en-US") : "n/a";
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
    <WidgetCard error={error} loading={loading} subtitle="Inventory" title="Availability">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="Stock" value={formatNumber(inventory.stock)} />
        <ProductDetailMetric label="Reserved" value={formatNumber(inventory.reserved)} />
        <ProductDetailMetric label="Available" value={formatNumber(inventory.available)} />
        <ProductDetailMetric
          label="Days left"
          value={typeof inventory.daysLeft === "number" ? `${inventory.daysLeft} days` : "n/a"}
        />
        <ProductDetailMetric label="Warehouse" value={inventory.warehouse} />
        <ProductDetailMetric label="Forecast" value={inventory.forecast} />
      </div>
    </WidgetCard>
  );
}
