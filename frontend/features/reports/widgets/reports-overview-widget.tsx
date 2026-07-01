import { StatusBadge } from "@/shared/status";
import { formatOptionalValue, localizeStatus } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { ReportSummary } from "@/features/reports/types";

export function ReportsOverviewWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: ReportSummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: summary.systemStatus, tone: "healthy" }}
      subtitle="Обзор отчетов"
      title="Центр отчетов"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Количество отчетов</div>
          <div className="mt-2 text-lg font-semibold">{summary.reportCount}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Последний отчет</div>
          <div className="mt-2 text-lg font-semibold">{summary.latestReport}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Последняя синхронизация</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.latestSync)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Последний CEO Report</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.latestCeoReport)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Последний Profit Audit</div>
          <div className="mt-2 text-lg font-semibold">{formatOptionalValue(summary.latestProfitAudit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Статус системы</div>
          <div className="mt-2 text-lg font-semibold">{localizeStatus(summary.systemStatus)}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusBadge tone="healthy">{localizeStatus(summary.systemStatus)}</StatusBadge>
        <StatusBadge tone="accent">{summary.latestReport}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
