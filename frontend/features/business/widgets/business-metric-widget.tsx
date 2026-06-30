import { WidgetCard } from "@/shared/widgets";
import type { BusinessMetric } from "@/features/business/types";

export function BusinessMetricWidget({
  metric,
  loading = false,
  error = null
}: {
  metric: BusinessMetric;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: metric.delta, tone: metric.tone }}
      subtitle={metric.value}
      title={metric.label}
    >
      <p className="text-sm leading-6 text-[var(--ink-soft)]">{metric.note}</p>
    </WidgetCard>
  );
}
