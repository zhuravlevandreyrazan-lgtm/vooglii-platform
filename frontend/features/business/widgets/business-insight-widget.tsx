import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { BusinessInsight } from "@/features/business/types";

export function BusinessInsightWidget({
  insight,
  loading = false,
  error = null,
  updatedAt
}: {
  insight: BusinessInsight;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{
        label: `Confidence ${insight.confidence}`,
        tone:
          insight.confidence === "high"
            ? "healthy"
            : insight.confidence === "medium"
              ? "watch"
              : "neutral"
      }}
      subtitle="Business Insight"
      title="Business Insight"
      updatedAt={updatedAt}
    >
      <div className="space-y-4">
        <p className="text-sm leading-7 text-[var(--ink-soft)]">{insight.summary}</p>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              Strengths
            </div>
            <div className="mt-3 space-y-2">
              {insight.strengths.slice(0, 2).map((item) => (
                <div key={item} className="text-sm leading-6">{item}</div>
              ))}
            </div>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              Weaknesses
            </div>
            <div className="mt-3 space-y-2">
              {insight.weaknesses.slice(0, 2).map((item) => (
                <div key={item} className="text-sm leading-6">{item}</div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {insight.risks.slice(0, 2).map((item) => (
            <StatusBadge key={item} tone="risk">{item}</StatusBadge>
          ))}
          {insight.opportunities.slice(0, 2).map((item) => (
            <StatusBadge key={item} tone="accent">{item}</StatusBadge>
          ))}
        </div>
      </div>
    </WidgetCard>
  );
}
