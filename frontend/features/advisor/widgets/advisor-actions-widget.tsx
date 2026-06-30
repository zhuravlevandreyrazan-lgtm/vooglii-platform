import Link from "next/link";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorAction } from "@/features/advisor/types";

export function AdvisorActionsWidget({
  actions,
  loading = false,
  error = null
}: {
  actions: AdvisorAction[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={actions.length === 0}
      emptyMessage="Advisor navigation actions will appear here when routes are available."
      error={error}
      loading={loading}
      subtitle="Navigation actions"
      title="Advisor Actions"
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {actions.map((action) => (
          <Link
            key={action.id}
            className="rounded-[22px] border border-[var(--line)] bg-white/70 px-4 py-4 text-sm font-semibold transition hover:bg-white"
            href={action.href}
          >
            {action.label}
          </Link>
        ))}
      </div>
    </WidgetCard>
  );
}
