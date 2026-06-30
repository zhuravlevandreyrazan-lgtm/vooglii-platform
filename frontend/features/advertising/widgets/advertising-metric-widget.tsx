import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingMetric } from "@/features/advertising/types";

export function AdvertisingMetricWidget({
  metric,
  loading = false,
  error = null
}: {
  metric: AdvertisingMetric;
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
