import { SeverityBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductInsight } from "@/features/product-details/types";

export function ProductInsightWidget({
  insight,
  loading = false,
  error = null
}: {
  insight: ProductInsight;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="AI Insight" title="Backend-ready analysis">
      <div className="space-y-5">
        <p className="text-sm leading-7 text-[var(--ink)]">{insight.summary}</p>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <div className="flex items-center gap-3">
              <SeverityBadge severity="high" />
              <p className="text-sm font-semibold">Top risk</p>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{insight.topRisk}</p>
          </div>

          <div className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <div className="flex items-center gap-3">
              <SeverityBadge severity="medium" />
              <p className="text-sm font-semibold">Top opportunity</p>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{insight.topOpportunity}</p>
          </div>
        </div>

        <div className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
          <p className="text-sm font-semibold">Recommendation</p>
          <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{insight.recommendation}</p>
        </div>

        <div className="grid gap-3">
          {insight.evidence.map((item) => (
            <div key={item.id} className="rounded-[18px] border border-[var(--line)] bg-white p-4">
              <p className="text-sm font-semibold">{item.label}</p>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </WidgetCard>
  );
}
