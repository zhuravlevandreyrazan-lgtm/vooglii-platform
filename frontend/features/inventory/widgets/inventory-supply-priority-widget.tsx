import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { InventoryPriority } from "@/features/inventory/types";

export function InventorySupplyPriorityWidget({
  priorities,
  loading = false,
  error = null
}: {
  priorities: InventoryPriority[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={priorities.length === 0}
      emptyMessage="Supply priority items will appear here when backend returns priority data."
      error={error}
      loading={loading}
      subtitle="Supply priority"
      title="Supply Priority"
    >
      <div className="space-y-3">
        {priorities.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{item.level.toUpperCase()}</div>
              <SeverityBadge severity={item.level} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.reason}</p>
            <p className="mt-3 text-sm font-semibold">{item.recommendation}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
