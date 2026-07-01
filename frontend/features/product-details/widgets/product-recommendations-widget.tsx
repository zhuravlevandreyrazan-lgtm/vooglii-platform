import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductRecommendation } from "@/features/product-details/types";

export function ProductRecommendationsWidget({
  recommendations,
  loading = false,
  error = null
}: {
  recommendations: ProductRecommendation[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Что сделать по товару" title="План действий">
      <div className="space-y-4">
        {recommendations.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <div className="flex flex-wrap items-center gap-3">
              <SeverityBadge severity={item.priority} />
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
                Уверенность: {item.confidence}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink)]">{item.reason}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.expectedEffect}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
