import Link from "next/link";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventorySku } from "@/features/inventory/types";

function formatMetric(value: number | null | undefined, suffix = "") {
  if (value === null || value === undefined) {
    return "Нет данных";
  }
  return `${value.toLocaleString("ru-RU")}${suffix}`;
}

export function InventoryTableWidget({
  items,
  loading = false,
  error = null
}: {
  items: InventorySku[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={items.length === 0}
      emptyMessage="Данные появятся после первой синхронизации остатков и продаж."
      error={error}
      loading={loading}
      subtitle="Реальные сигналы по SKU"
      title="Остатки по товарам"
    >
      <div className="space-y-3">
        {items.map((item) => (
          <Link
            key={item.sku}
            className="block rounded-[22px] border border-[var(--line)] bg-white/70 p-4 transition hover:bg-white"
            href={`/inventory/${item.sku}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.name ?? item.sku}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.sku}</div>
              </div>
              <StatusBadge tone={item.status.tone}>{item.status.label}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Остаток</div>
                <div className="mt-1 text-sm font-semibold">{formatMetric(item.stock)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Продаж в день</div>
                <div className="mt-1 text-sm font-semibold">{formatMetric(item.salesVelocity)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Покрытие, дни</div>
                <div className="mt-1 text-sm font-semibold">{formatMetric(item.coverageDays ?? item.daysLeft)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выручка</div>
                <div className="mt-1 text-sm font-semibold">{formatMetric(item.linkedRevenue)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Реклама</div>
                <div className="mt-1 text-sm font-semibold">{formatMetric(item.linkedAdvertisingSpend)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Склад</div>
                <div className="mt-1 text-sm font-semibold">{item.warehouse}</div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatusBadge tone="neutral">{item.risk ?? item.health}</StatusBadge>
              <StatusBadge tone={item.scaleAllowed ? "accent" : "watch"}>{item.recommendation}</StatusBadge>
            </div>
          </Link>
        ))}
      </div>
    </WidgetCard>
  );
}
