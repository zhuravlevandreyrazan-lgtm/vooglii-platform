import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryWarehouse } from "@/features/inventory/types";

function toneForHealth(value: string) {
  const normalized = value.toLowerCase();
  if (normalized.includes("strong")) {
    return "healthy" as const;
  }
  if (normalized.includes("watch")) {
    return "watch" as const;
  }
  return "neutral" as const;
}

export function InventoryWarehouseWidget({
  warehouses,
  loading = false,
  error = null
}: {
  warehouses: InventoryWarehouse[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={warehouses.length === 0}
      emptyMessage="Аналитика по складам появится здесь, когда станут доступны данные по площадкам хранения."
      error={error}
      loading={loading}
      subtitle="Состояние складов"
      title="Склады"
    >
      <div className="space-y-3">
        {warehouses.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{item.warehouse}</div>
              <StatusBadge tone={toneForHealth(item.health)}>{item.status}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Текущий остаток</div>
                <div className="mt-1 text-sm font-semibold">{item.currentStock ?? "Нет данных"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Критичные SKU</div>
                <div className="mt-1 text-sm font-semibold">{item.criticalSku ?? "Нет данных"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Прогноз</div>
                <div className="mt-1 text-sm font-semibold">{item.forecast}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Состояние</div>
                <div className="mt-1 text-sm font-semibold">{item.health}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
