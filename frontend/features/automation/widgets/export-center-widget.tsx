import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ExportFormat, ExportPreset } from "@/features/automation/types";

export function ExportCenterWidget({
  exports,
  pendingAction = false,
  onGenerate,
  selectedWorkspace,
  selectedFormat,
  loading = false,
  error = null
}: {
  exports: ExportPreset[];
  pendingAction?: boolean;
  onGenerate: (payload: { workspace: string; format: ExportFormat; name?: string }) => Promise<void>;
  selectedWorkspace?: string | null;
  selectedFormat?: string | null;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={exports.length === 0}
      emptyMessage="Export presets will appear here when automation metadata is available."
      error={error}
      loading={loading}
      subtitle="Generate placeholder exports"
      title="Export Center"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {exports.map((item) => (
          <div key={item.id} className="rounded-[24px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-base font-semibold">{item.name}</p>
              <StatusBadge tone={item.status.tone}>{item.status.label}</StatusBadge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge tone="neutral">{item.workspace}</StatusBadge>
              <StatusBadge tone="accent">{item.format}</StatusBadge>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">{item.description}</p>
            <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
              Owner {item.owner}
            </p>
            {item.organizationName || item.cabinetName ? (
              <p className="mt-2 text-xs text-[var(--ink-soft)]">
                {[item.organizationName, item.cabinetName].filter(Boolean).join(" • ")}
              </p>
            ) : null}
            <div className="mt-4">
              <Button
                disabled={
                  pendingAction ||
                  (selectedWorkspace !== null && selectedWorkspace !== undefined && selectedWorkspace.length > 0 && item.workspace !== selectedWorkspace) ||
                  (selectedFormat !== null && selectedFormat !== undefined && selectedFormat.length > 0 && item.format !== selectedFormat)
                }
                onClick={() => void onGenerate({ workspace: item.workspace, format: item.format, name: item.name })}
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
