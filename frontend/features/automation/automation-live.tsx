"use client";

import { useSearchParams } from "next/navigation";
import { useAutomationData } from "@/features/automation/hooks/use-automation-data";
import { AutomationScreen } from "@/features/automation/automation-screen";
import { useWorkspaceContext } from "@/shared/workspace-context";

export function AutomationLive() {
  const searchParams = useSearchParams();
  const workspace = useWorkspaceContext();
  const selectedWorkspace = searchParams.get("workspace");
  const selectedFormat = searchParams.get("format");
  const sku = searchParams.get("sku");
  const {
    data,
    loading,
    error,
    actionMessage,
    pendingAction,
    lastUpdated,
    diagnostics,
    generateExport,
    toggleSchedule
  } = useAutomationData();

  return (
    <AutomationScreen
      actionMessage={actionMessage}
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      onGenerate={(payload) => generateExport({ ...payload, sku: payload.sku ?? sku ?? undefined })}
      onToggleSchedule={toggleSchedule}
      pendingAction={pendingAction}
      selectedFormat={selectedFormat}
      selectedWorkspace={selectedWorkspace}
      workspaceContext={{
        organizationId: workspace.organization?.id ?? null,
        organization: workspace.organization?.name ?? null,
        cabinetId: workspace.cabinet?.id ?? null,
        cabinet: workspace.cabinet?.name ?? null,
        mode: workspace.mode
      }}
    />
  );
}
