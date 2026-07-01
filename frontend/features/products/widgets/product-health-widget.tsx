import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductCard } from "@/features/products/types";

export function ProductHealthWidget({
  products,
  loading = false,
  error = null
}: {
  products: ProductCard[];
  loading?: boolean;
  error?: string | null;
}) {
  const featured = products[0];

  return (
    <WidgetCard
      empty={!featured}
      emptyMessage="Состояние товара появится здесь, когда станут доступны данные хотя бы по одному SKU."
      error={error}
      loading={loading}
      subtitle="Featured SKU health"
      title="Product Health Panel"
    >
      {featured ? (
        <div className="space-y-4">
          <div>
            <div className="text-base font-semibold">{featured.name}</div>
            <div className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              {featured.sku}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ABC</div>
              <div className="mt-2 text-lg font-semibold">{featured.health.abc}</div>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">XYZ</div>
              <div className="mt-2 text-lg font-semibold">{featured.health.xyz}</div>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Forecast</div>
              <div className="mt-2 text-lg font-semibold">{featured.health.forecast}</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <HealthBadge label={featured.health.health} />
            <StatusBadge tone={featured.status.tone}>{featured.health.status}</StatusBadge>
            <StatusBadge tone="risk">Risk {featured.health.riskLevel}</StatusBadge>
          </div>
        </div>
      ) : null}
    </WidgetCard>
  );
}
