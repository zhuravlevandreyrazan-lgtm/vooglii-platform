import { WidgetCard } from "@/shared/widgets";
import type { FinanceMetric } from "@/features/finance/types";

export function FinanceMetricWidget({
  metric,
  loading = false,
  error = null
}: {
  metric: FinanceMetric;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: metric.label, tone: metric.tone }}
      subtitle={metric.value}
      title={metric.label}
    >
      <p className="text-sm leading-6 text-[var(--ink-soft)]">{metric.note}</p>
    </WidgetCard>
  );
}
