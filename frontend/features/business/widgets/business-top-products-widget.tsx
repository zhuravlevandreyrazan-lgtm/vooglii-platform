import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { BusinessProduct } from "@/features/business/types";

function toneForStatus(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes("pressure")) {
    return "watch" as const;
  }
  if (normalized.includes("scal")) {
    return "accent" as const;
  }
  return "healthy" as const;
}

export function BusinessTopProductsWidget({
  products,
  loading = false,
  error = null
}: {
  products: BusinessProduct[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={products.length === 0}
      emptyMessage="Top products will appear here when the business snapshot includes assortment-level data."
      error={error}
      loading={loading}
      subtitle="Top products"
      title="Top Products"
    >
      <div className="space-y-3">
        {products.map((product) => (
          <div key={product.sku} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{product.title}</div>
                <div className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  {product.sku}
                </div>
              </div>
              <StatusBadge tone={toneForStatus(product.status)}>{product.status}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Revenue</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(product.revenue)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Profit</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(product.profit)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Margin</div>
                <div className="mt-1 text-sm font-semibold">{formatPercent(product.margin)}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
