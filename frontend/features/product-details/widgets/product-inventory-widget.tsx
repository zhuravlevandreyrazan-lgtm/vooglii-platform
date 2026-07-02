import { ProductDetailMetric } from "@/features/product-details/components/product-detail-metric";
import type { ProductInventory } from "@/features/product-details/types";
import { WidgetCard } from "@/shared/widgets";

function formatNumber(value: number | null) {
  return typeof value === "number" ? value.toLocaleString("ru-RU") : "РќРµС‚ РґР°РЅРЅС‹С…";
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
    <WidgetCard error={error} loading={loading} subtitle="РћСЃС‚Р°С‚РєРё" title="РќР°Р»РёС‡РёРµ">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProductDetailMetric label="РћСЃС‚Р°С‚РѕРє" value={formatNumber(inventory.stock)} />
        <ProductDetailMetric label="Р РµР·РµСЂРІ" value={formatNumber(inventory.reserved)} />
        <ProductDetailMetric label="Р”РѕСЃС‚СѓРїРЅРѕ" value={formatNumber(inventory.available)} />
        <ProductDetailMetric
          label="Р”РЅРµР№ Р·Р°РїР°СЃР°"
          value={typeof inventory.daysLeft === "number" ? `${inventory.daysLeft} РґРЅРµР№` : "РќРµС‚ РґР°РЅРЅС‹С…"}
        />
        <ProductDetailMetric label="РЎРєР»Р°Рґ" value={inventory.warehouse} />
        <ProductDetailMetric label="РџСЂРѕРіРЅРѕР·" value={inventory.forecast} />
      </div>
    </WidgetCard>
  );
}
