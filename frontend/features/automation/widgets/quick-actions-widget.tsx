import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ExportFormat, QuickActionItem } from "@/features/automation/types";

export function QuickActionsWidget({
  actions,
  pendingAction = false,
  onGenerate,
  loading = false,
  error = null
}: {
  actions: QuickActionItem[];
  pendingAction?: boolean;
  onGenerate: (payload: { workspace: string; format: ExportFormat; name?: string }) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={actions.length === 0}
      emptyMessage="Быстрые действия появятся здесь после загрузки сценариев автоматизации."
      error={error}
      loading={loading}
      subtitle="Fast operational shortcuts"
      title="Quick Actions"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {actions.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-base font-semibold">{item.label}</p>
              <StatusBadge tone="accent">{item.format}</StatusBadge>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
            <div className="mt-3">
              <StatusBadge tone="neutral">{item.workspace}</StatusBadge>
            </div>
            <div className="mt-4">
              <Button
                disabled={pendingAction}
                onClick={() => void onGenerate({ workspace: item.workspace, format: item.format, name: item.label })}
                variant="secondary"
              >
                Generate
              </Button>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
