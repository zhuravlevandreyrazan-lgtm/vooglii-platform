import Link from "next/link";
import { SeverityBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorRecommendation } from "@/features/advisor/types";

export function AdvisorRecommendationsWidget({
  recommendations,
  loading = false,
  error = null
}: {
  recommendations: AdvisorRecommendation[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={recommendations.length === 0}
      emptyMessage="Рекомендации появятся после получения данных от backend."
      error={error}
      loading={loading}
      subtitle="Рекомендации для действий"
      title="Рекомендации"
    >
      <div className="space-y-3">
        {recommendations.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-base font-semibold">{item.title}</div>
              <SeverityBadge severity={item.priority} />
            </div>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{item.reason}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="accent">{item.expectedEffect}</StatusBadge>
              <StatusBadge tone="neutral">Уверенность: {item.confidence}</StatusBadge>
              <StatusBadge tone="watch">Источник: {item.source}</StatusBadge>
              <StatusBadge tone="healthy">{item.status}</StatusBadge>
            </div>
            <div className="mt-4">
              <Link className="text-sm font-semibold text-[var(--accent-strong)]" href={item.href}>
                Открыть связанный раздел
              </Link>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
