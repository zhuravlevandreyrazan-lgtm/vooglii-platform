import Link from "next/link";
import { WidgetCard } from "@/shared/widgets";
import type { ProductAction } from "@/features/product-details/types";

function actionClass(enabled: boolean) {
  return enabled
    ? "border-[var(--line)] bg-white hover:-translate-y-0.5 hover:border-[var(--accent)] hover:bg-[var(--panel)]"
    : "cursor-not-allowed border-[var(--line)] bg-[var(--panel)] text-[var(--ink-soft)] opacity-70";
}

export function ProductQuickActionsWidget({
  actions,
  loading = false,
  error = null
}: {
  actions: ProductAction[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Quick Actions" title="Operator shortcuts">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {actions.map((action) =>
          action.type === "link" && action.href ? (
            <Link
              key={action.id}
              className={`rounded-[20px] border px-4 py-3 text-sm font-semibold transition ${actionClass(action.enabled)}`}
              href={action.href}
            >
              {action.label}
            </Link>
          ) : (
            <button
              key={action.id}
              className={`rounded-[20px] border px-4 py-3 text-left text-sm font-semibold transition ${actionClass(action.enabled)}`}
              disabled
              type="button"
            >
              {action.label}
            </button>
          )
        )}
      </div>
    </WidgetCard>
  );
}
