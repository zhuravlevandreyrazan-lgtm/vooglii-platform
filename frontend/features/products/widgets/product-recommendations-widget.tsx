import { SeverityBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductRecommendation } from "@/features/products/types";

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
    <WidgetCard
      empty={recommendations.length === 0}
      emptyMessage="SKU action plan recommendations will appear here when backend returns product actions."
      error={error}
      loading={loading}
      subtitle="SKU action plan"
      title="Recommendations"
    >
      <div className="space-y-3">
        {recommendations.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.sku}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.recommendation}</div>
              </div>
              <SeverityBadge severity={item.priority} />
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.reason}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="accent">{item.expectedEffect}</StatusBadge>
              <StatusBadge tone="neutral">Confidence {item.confidence}</StatusBadge>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
