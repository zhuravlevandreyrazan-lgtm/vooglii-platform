import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ReportExport } from "@/features/reports/types";

export function ReportExportCenterWidget({
  exports,
  loading = false,
  error = null
}: {
  exports: ReportExport[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={exports.length === 0}
      emptyMessage="Форматы выгрузки появятся здесь после загрузки метаданных экспорта."
      error={error}
      loading={loading}
      subtitle="Export center"
      title="Export Center"
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {exports.map((item) => (
          <div key={item.format} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="text-base font-semibold">{item.format}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="accent">{item.status}</StatusBadge>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
