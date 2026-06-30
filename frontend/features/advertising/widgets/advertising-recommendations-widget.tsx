import { SeverityBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingRecommendation } from "@/features/advertising/types";

export function AdvertisingRecommendationsWidget({
  recommendations,
  loading = false,
  error = null
}: {
  recommendations: AdvertisingRecommendation[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={recommendations.length === 0}
      emptyMessage="Campaign recommendations will appear here when backend returns recommendation payloads."
      error={error}
      loading={loading}
      subtitle="Campaign recommendations"
      title="Campaign Recommendation Panel"
    >
      <div className="space-y-3">
        {recommendations.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.campaign}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.recommendation}</div>
              </div>
              <SeverityBadge severity={item.severity} />
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
