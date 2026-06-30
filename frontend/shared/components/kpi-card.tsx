import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
import type { HealthMetric } from "@/types/platform";

export function KpiCard({ metric }: { metric: HealthMetric }) {
  return (
    <Card className="min-h-40">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-[var(--ink-soft)]">{metric.label}</p>
        <StatusBadge tone={metric.tone}>{metric.delta}</StatusBadge>
      </div>
      <div className="mt-6 text-3xl font-semibold tracking-[-0.04em]">{metric.value}</div>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{metric.note}</p>
    </Card>
  );
}
