import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductCard } from "@/features/products/types";

export function ProductInventoryPreviewWidget({
  products,
  loading = false,
  error = null
}: {
  products: ProductCard[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={products.length === 0}
      emptyMessage="Предварительный обзор остатков появится здесь после загрузки складской аналитики."
      error={error}
      loading={loading}
      subtitle="Inventory preview"
      title="Inventory Preview"
    >
      <div className="space-y-3">
        {products.slice(0, 3).map((product) => (
          <div key={product.sku} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{product.name}</div>
                <div className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  {product.sku}
                </div>
              </div>
              <StatusBadge tone={product.status.tone}>{product.health.riskLevel}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Stock</div>
                <div className="mt-1 text-sm font-semibold">{product.metrics.stock ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Days Left</div>
                <div className="mt-1 text-sm font-semibold">{product.metrics.daysLeft ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Forecast</div>
                <div className="mt-1 text-sm font-semibold">{product.health.forecast}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Warehouse</div>
                <div className="mt-1 text-sm font-semibold">{product.warehouse}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
