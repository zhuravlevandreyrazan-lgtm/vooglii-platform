import Link from "next/link";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventorySku } from "@/features/inventory/types";

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
      emptyMessage="Inventory table will appear here when backend returns stock analytics rows."
      error={error}
      loading={loading}
      subtitle="Main inventory table"
      title="Inventory Table"
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
                <div className="text-base font-semibold">{item.sku}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.recommendation}</div>
              </div>
              <StatusBadge tone={item.status.tone}>{item.status.label}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Stock</div>
                <div className="mt-1 text-sm font-semibold">{item.stock ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Reserved</div>
                <div className="mt-1 text-sm font-semibold">{item.reserved ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Available</div>
                <div className="mt-1 text-sm font-semibold">{item.available ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Days Left</div>
                <div className="mt-1 text-sm font-semibold">{item.daysLeft ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Warehouse</div>
                <div className="mt-1 text-sm font-semibold">{item.warehouse}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Priority</div>
                <div className="mt-1 text-sm font-semibold">{item.priority}</div>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <StatusBadge tone="neutral">{item.health}</StatusBadge>
              <StatusBadge tone="accent">{item.forecast}</StatusBadge>
            </div>
          </Link>
        ))}
      </div>
    </WidgetCard>
  );
}
