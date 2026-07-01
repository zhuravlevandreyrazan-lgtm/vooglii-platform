import Link from "next/link";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { AdvisorEvidence } from "@/features/advisor/types";

export function AdvisorEvidenceWidget({
  evidence,
  loading = false,
  error = null
}: {
  evidence: AdvisorEvidence[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={evidence.length === 0}
      emptyMessage="Основания рекомендаций появятся после получения данных от backend."
      error={error}
      loading={loading}
      subtitle="Почему советник рекомендует именно это"
      title="Основания"
    >
      <div className="space-y-3">
        {evidence.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.source}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.reason}</div>
              </div>
              <StatusBadge tone="watch">{item.workspace}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {item.metrics.map((metric) => (
                <StatusBadge key={metric} tone="neutral">{metric}</StatusBadge>
              ))}
            </div>
            <div className="mt-4">
              <Link className="text-sm font-semibold text-[var(--accent-strong)]" href={item.href}>
                Открыть раздел {item.workspace}
              </Link>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
