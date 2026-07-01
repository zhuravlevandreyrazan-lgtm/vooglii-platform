import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorSummary } from "@/features/advisor/types";

export function AdvisorOverviewWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: AdvisorSummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: summary.businessStatus, tone: "watch" }}
      subtitle="Обзор советника"
      title="Сводка советника"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Общее состояние</div>
          <div className="mt-2 text-lg font-semibold">{summary.overallHealth}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Критичные риски</div>
          <div className="mt-2 text-lg font-semibold">{summary.criticalRisks}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Точки роста</div>
          <div className="mt-2 text-lg font-semibold">{summary.topOpportunities}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Рекомендации</div>
          <div className="mt-2 text-lg font-semibold">{summary.recommendationCount}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Статус бизнеса</div>
          <div className="mt-2 text-lg font-semibold">{summary.businessStatus}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={summary.overallHealth} />
        <StatusBadge tone="risk">Риски: {summary.criticalRisks}</StatusBadge>
        <StatusBadge tone="accent">Точки роста: {summary.topOpportunities}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
