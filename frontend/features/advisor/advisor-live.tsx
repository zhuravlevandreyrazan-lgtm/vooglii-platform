"use client";

import { AdvisorScreen } from "@/features/advisor/advisor-screen";
import { useAdvisorData } from "@/features/advisor/hooks/use-advisor-data";
import { useWorkspaceContext } from "@/shared/workspace-context";

export function AdvisorLive() {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useAdvisorData();
  const workspace = useWorkspaceContext();

  return (
    <AdvisorScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
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
