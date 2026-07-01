import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryRestockPlan } from "@/features/inventory/types";

export function InventoryRestockPlanWidget({
  plan,
  loading = false,
  error = null
}: {
  plan: InventoryRestockPlan[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={plan.length === 0}
      emptyMessage="План пополнения появится здесь, когда станут доступны рекомендации по остаткам."
      error={error}
      loading={loading}
      subtitle="Рекомендации по пополнению"
      title="План пополнения"
    >
      <div className="space-y-3">
        {plan.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.sku}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.reason}</div>
              </div>
              <SeverityBadge severity={item.priority} />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Рекомендуемое количество</div>
                <div className="mt-1 text-sm font-semibold">{item.recommendedQuantity ?? "Нет данных"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Ожидаемое покрытие</div>
                <div className="mt-1 text-sm font-semibold">{item.expectedCoverage}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Склад</div>
                <div className="mt-1 text-sm font-semibold">{item.warehouse}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
