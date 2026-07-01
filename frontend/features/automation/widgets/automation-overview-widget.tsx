import { WidgetCard } from "@/shared/widgets";
import type { AutomationSummary } from "@/features/automation/types";

export function AutomationOverviewWidget({
  summary,
  owner,
  organization,
  cabinet,
  loading = false,
  error = null,
  selectedWorkspace
}: {
  summary: AutomationSummary;
  owner: string;
  organization: string;
  cabinet: string;
  selectedWorkspace?: string | null;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Ключевые показатели автоматизации" title="Автоматизация">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выгрузки</p>
          <p className="mt-2 text-2xl font-semibold">{summary.exportCount}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Расписания</p>
          <p className="mt-2 text-2xl font-semibold">{summary.scheduleCount}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Активные задачи</p>
          <p className="mt-2 text-2xl font-semibold">{summary.activeJobs}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Ответственный</p>
          <p className="mt-2 text-sm font-semibold">{owner}</p>
          <p className="mt-1 text-sm text-[var(--ink-soft)]">{organization}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Контекст</p>
          <p className="mt-2 text-sm font-semibold">{selectedWorkspace ?? "Все разделы"}</p>
          <p className="mt-1 text-sm text-[var(--ink-soft)]">{cabinet}</p>
        </div>
      </div>
    </WidgetCard>
  );
}
