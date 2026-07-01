import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
import { formatOptionalValue } from "@/shared/ui/status-labels";
import type { HealthMetric } from "@/types/platform";

export function KpiCard({ metric }: { metric: HealthMetric }) {
  const hasValue = metric.value && metric.value !== "Нет данных";

  return (
    <Card className="min-h-[168px] overflow-hidden rounded-[22px]">
      <div className="flex items-start justify-between gap-3">
        <p className="pr-3 text-[13px] font-semibold leading-5 text-[var(--ink-soft)]">{metric.label}</p>
        <StatusBadge className="max-w-[8.5rem] shrink-0" tone={metric.tone}>
          {formatOptionalValue(metric.delta, "Ожидаем обновление")}
        </StatusBadge>
      </div>
      <div className="mt-5 text-[1.85rem] font-semibold tracking-[-0.05em]">
        {formatOptionalValue(metric.value, "Нет данных")}
      </div>
      <p className="mt-2 max-w-[28ch] text-sm leading-6 text-[var(--ink-soft)]">
        {hasValue ? metric.note : "Появится после синхронизации кабинета."}
      </p>
    </Card>
  );
}
