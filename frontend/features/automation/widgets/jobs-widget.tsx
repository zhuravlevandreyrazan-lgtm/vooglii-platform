import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { JobItem } from "@/features/automation/types";

export function JobsWidget({
  jobs,
  loading = false,
  error = null
}: {
  jobs: JobItem[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={jobs.length === 0}
      emptyMessage="Фоновые задачи появятся здесь после загрузки очереди."
      error={error}
      loading={loading}
      subtitle="Job queue"
      title="Jobs"
    >
      <div className="space-y-3">
        {jobs.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-semibold">{item.id}</p>
                <p className="mt-1 text-sm text-[var(--ink-soft)]">{item.workspace} • {item.type} • owner {item.owner}</p>
                {item.organizationName || item.cabinetName ? (
                  <p className="mt-1 text-xs text-[var(--ink-soft)]">
                    {[item.organizationName, item.cabinetName].filter(Boolean).join(" • ")}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone={item.status === "failed" ? "risk" : item.status === "completed" ? "healthy" : "watch"}>
                  {item.status}
                </StatusBadge>
                <StatusBadge tone="neutral">{item.progress}%</StatusBadge>
              </div>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-[var(--panel-strong)]">
              <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${Math.max(0, Math.min(100, item.progress))}%` }} />
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Started</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.startedAt ?? "n/a"}</p>
              </div>
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Finished</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.finishedAt ?? "In progress"}</p>
              </div>
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Duration</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.duration ?? "Calculating"}</p>
              </div>
            </div>
            {item.message ? <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.message}</p> : null}
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
