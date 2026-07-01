import { formatCurrency } from "@/features/command-center/formatters";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { formatOptionalValue, localizeStatus } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { FinanceSummary } from "@/features/finance/types";

export function FinanceSummaryWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: FinanceSummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: summary.status, tone: "watch" }}
      subtitle="Сводка по финансам"
      title="Финансовая сводка"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Операционная прибыль</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.operatingProfit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Официальная прибыль</div>
          <div className="mt-2 text-lg font-semibold">{summary.officialProfit === null ? "Нет данных" : formatCurrency(summary.officialProfit)}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Расхождение</div>
          <div className="mt-2 text-lg font-semibold">{formatCurrency(summary.difference)}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <HealthBadge label={summary.health} score={summary.trustScore ?? undefined} />
        <StatusBadge tone="risk">Доверие: {formatOptionalValue(summary.trustScore)}</StatusBadge>
        <StatusBadge tone="neutral">{localizeStatus(summary.status)}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
