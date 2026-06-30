import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductSummary } from "@/features/products/types";

export function ProductsSummaryWidget({
  summary,
  loading = false,
  error = null,
  updatedAt
}: {
  summary: ProductSummary;
  loading?: boolean;
  error?: string | null;
  updatedAt?: string;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={{ label: `${summary.skuCount} SKU`, tone: "neutral" }}
      subtitle="Products Summary"
      title="Products Summary"
      updatedAt={updatedAt}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Active SKU</div>
          <div className="mt-2 text-lg font-semibold">{summary.activeSku}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Problem SKU</div>
          <div className="mt-2 text-lg font-semibold">{summary.problemSku}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">SKU at Risk</div>
          <div className="mt-2 text-lg font-semibold">{summary.riskSku}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Growth SKU</div>
          <div className="mt-2 text-lg font-semibold">{summary.growthSku}</div>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">SKU Count</div>
          <div className="mt-2 text-lg font-semibold">{summary.skuCount}</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <StatusBadge tone="healthy">Active {summary.activeSku}</StatusBadge>
        <StatusBadge tone="watch">Problems {summary.problemSku}</StatusBadge>
        <StatusBadge tone="risk">Risk {summary.riskSku}</StatusBadge>
      </div>
    </WidgetCard>
  );
}
