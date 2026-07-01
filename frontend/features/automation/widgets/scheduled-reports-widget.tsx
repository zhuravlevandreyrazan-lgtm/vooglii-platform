import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ScheduleItem } from "@/features/automation/types";

function formatDate(value: string | null) {
  return value ?? "Еще не запускалось";
}

export function ScheduledReportsWidget({
  schedules,
  pendingAction = false,
  onToggle,
  loading = false,
  error = null
}: {
  schedules: ScheduleItem[];
  pendingAction?: boolean;
  onToggle: (scheduleId: string, enabled: boolean) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={schedules.length === 0}
      emptyMessage="Запланированные отчеты появятся после загрузки расписаний."
      error={error}
      loading={loading}
      subtitle="Автоматические выгрузки"
      title="Расписания"
    >
      <div className="space-y-3">
        {schedules.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-semibold">{item.name}</p>
                <p className="mt-1 text-sm text-[var(--ink-soft)]">
                  {item.workspace} • {item.cadence} • {item.time} {item.timezone}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone={item.enabled ? "healthy" : "watch"}>
                  {item.enabled ? "Включено" : "На паузе"}
                </StatusBadge>
                <StatusBadge tone="neutral">{item.format}</StatusBadge>
              </div>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Последний запуск</p>
                <p className="mt-1 text-[var(--ink-soft)]">{formatDate(item.lastRunAt)}</p>
              </div>
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Следующий запуск</p>
                <p className="mt-1 text-[var(--ink-soft)]">{formatDate(item.nextRunAt)}</p>
              </div>
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Ответственный</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.owner}</p>
              </div>
            </div>
            <div className="mt-4">
              <Button
                disabled={pendingAction}
                onClick={() => void onToggle(item.id, !item.enabled)}
                variant={item.enabled ? "ghost" : "secondary"}
              >
                {item.enabled ? "Остановить расписание" : "Запустить расписание"}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
