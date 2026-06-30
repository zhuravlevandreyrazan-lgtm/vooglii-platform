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
    <WidgetCard
      error={error}
      loading={loading}
      subtitle="Automation overview"
      title="Automation Control"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Exports</p>
          <p className="mt-2 text-2xl font-semibold">{summary.exportCount}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Schedules</p>
          <p className="mt-2 text-2xl font-semibold">{summary.scheduleCount}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Active Jobs</p>
          <p className="mt-2 text-2xl font-semibold">{summary.activeJobs}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Owner</p>
          <p className="mt-2 text-sm font-semibold">{owner}</p>
          <p className="mt-1 text-sm text-[var(--ink-soft)]">{organization}</p>
        </div>
        <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Context</p>
          <p className="mt-2 text-sm font-semibold">{selectedWorkspace ?? "All workspaces"}</p>
          <p className="mt-1 text-sm text-[var(--ink-soft)]">{cabinet}</p>
        </div>
      </div>
    </WidgetCard>
  );
}
