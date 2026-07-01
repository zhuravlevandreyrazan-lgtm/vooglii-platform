import { StatusBadge } from "@/shared/status";
import { localizeStatus } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { ExportHistoryItem } from "@/features/automation/types";

export function ExportHistoryWidget({
  history,
  loading = false,
  error = null
}: {
  history: ExportHistoryItem[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={history.length === 0}
      emptyMessage="История выгрузок появится после первых экспортов."
      error={error}
      loading={loading}
      subtitle="Последние выгрузки"
      title="История выгрузок"
    >
      <div className="space-y-3">
        {history.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-semibold">{item.type}</p>
                <p className="mt-1 text-sm text-[var(--ink-soft)]">Ответственный: {item.owner}</p>
                {item.organizationName || item.cabinetName ? (
                  <p className="mt-1 text-xs text-[var(--ink-soft)]">
                    {[item.organizationName, item.cabinetName].filter(Boolean).join(" • ")}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone="accent">{item.format}</StatusBadge>
                <StatusBadge
                  tone={item.status.toLowerCase() === "completed" ? "healthy" : item.status.toLowerCase() === "failed" ? "risk" : "watch"}
                >
                  {localizeStatus(item.status)}
                </StatusBadge>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-[var(--ink-soft)]">
              <span>{item.date ?? "Нет данных"}</span>
              <span>{item.size ?? "Размер появится после выгрузки"}</span>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
