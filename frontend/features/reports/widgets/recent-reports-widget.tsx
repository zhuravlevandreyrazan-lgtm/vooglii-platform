import Link from "next/link";
import { formatOptionalValue, localizeStatus } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { ReportHistory } from "@/features/reports/types";

export function RecentReportsWidget({
  recent,
  loading = false,
  error = null
}: {
  recent: ReportHistory[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={recent.length === 0}
      emptyMessage="Последние отчеты появятся здесь, когда backend начнет возвращать историю генерации."
      error={error}
      loading={loading}
      subtitle="Последние отчеты"
      title="Недавние отчеты"
    >
      <div className="space-y-3">
        {recent.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{item.type}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{item.source}</div>
              </div>
              <div className="text-sm font-semibold">{localizeStatus(item.status)}</div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-[var(--ink-soft)]">
              <span>{formatOptionalValue(item.date)}</span>
              <Link className="font-semibold text-[var(--accent-strong)]" href={item.href}>
                Открыть связанный раздел
              </Link>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
