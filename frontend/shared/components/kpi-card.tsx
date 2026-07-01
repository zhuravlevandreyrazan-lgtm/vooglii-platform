import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
import { formatOptionalValue } from "@/shared/ui/status-labels";
import type { HealthMetric } from "@/types/platform";

export function KpiCard({ metric }: { metric: HealthMetric }) {
  return (
    <Card className="min-h-44 overflow-hidden">
      <div className="flex items-start justify-between gap-3">
        <p className="pr-3 text-sm font-semibold text-[var(--ink-soft)]">{metric.label}</p>
        <StatusBadge className="max-w-[9rem] shrink-0" tone={metric.tone}>
          {formatOptionalValue(metric.delta, "Нет данных")}
        </StatusBadge>
      </div>
      <div className="mt-6 text-3xl font-semibold tracking-[-0.04em]">
        {formatOptionalValue(metric.value, "Нет данных")}
      </div>
      <p className="mt-3 max-w-[32ch] text-sm leading-6 text-[var(--ink-soft)]">{metric.note}</p>
    </Card>
  );
}
