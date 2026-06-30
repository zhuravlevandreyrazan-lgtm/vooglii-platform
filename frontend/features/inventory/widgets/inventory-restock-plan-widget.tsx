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
      emptyMessage="Restock plan will appear here when backend returns replenishment recommendations."
      error={error}
      loading={loading}
      subtitle="Backend-ready restock plan"
      title="Restock Plan"
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
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Recommended Qty</div>
                <div className="mt-1 text-sm font-semibold">{item.recommendedQuantity ?? "n/a"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Expected Coverage</div>
                <div className="mt-1 text-sm font-semibold">{item.expectedCoverage}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Warehouse</div>
                <div className="mt-1 text-sm font-semibold">{item.warehouse}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
