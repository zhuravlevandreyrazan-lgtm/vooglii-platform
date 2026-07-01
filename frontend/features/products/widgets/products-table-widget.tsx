import Link from "next/link";
import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductCard } from "@/features/products/types";

export function ProductsTableWidget({
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
      emptyMessage="Таблица товаров появится здесь, когда станут доступны данные по SKU."
      error={error}
      loading={loading}
      subtitle="Основная таблица по SKU"
      title="Товары"
    >
      <div className="space-y-3">
        {products.map((product) => (
          <Link
            key={product.sku}
            className="block rounded-[22px] border border-[var(--line)] bg-white/70 p-4 transition hover:bg-white"
            href={`/products/${product.sku}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{product.name}</div>
                <div className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                  {product.sku}
                </div>
              </div>
              <StatusBadge tone={product.status.tone}>{product.status.label}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выручка</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(product.metrics.revenue)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Прибыль</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(product.metrics.profit)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Маржинальность</div>
                <div className="mt-1 text-sm font-semibold">{formatPercent(product.metrics.margin)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ROAS</div>
                <div className="mt-1 text-sm font-semibold">
                  {product.metrics.roas === null ? "n/a" : `${product.metrics.roas.toFixed(1)}x`}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ACOS</div>
                <div className="mt-1 text-sm font-semibold">{formatPercent(product.metrics.acos)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Остаток</div>
                <div className="mt-1 text-sm font-semibold">
                  {product.metrics.stock === null ? "Нет данных" : product.metrics.stock.toLocaleString("ru-RU")}
                </div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <HealthBadge label={product.health.health} />
              <StatusBadge tone="neutral">Дней запаса: {product.metrics.daysLeft ?? "Нет данных"}</StatusBadge>
              <StatusBadge tone="accent">{product.trend}</StatusBadge>
              <StatusBadge tone="watch">{product.recommendation}</StatusBadge>
            </div>
          </Link>
        ))}
      </div>
    </WidgetCard>
  );
}
