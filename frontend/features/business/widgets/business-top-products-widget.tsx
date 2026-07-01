import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { StatusBadge } from "@/shared/status";
import { localizeKnownText } from "@/shared/ui/status-labels";
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
      emptyMessage="Товары-лидеры появятся здесь, когда станут доступны данные по ассортименту."
      error={error}
      loading={loading}
      subtitle="Товары с наибольшим вкладом"
      title="Лидеры по ассортименту"
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
              <StatusBadge tone={toneForStatus(product.status)}>{localizeKnownText(product.status, "Норма")}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выручка</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(product.revenue)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Прибыль</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(product.profit)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Маржинальность</div>
                <div className="mt-1 text-sm font-semibold">{formatPercent(product.margin)}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
