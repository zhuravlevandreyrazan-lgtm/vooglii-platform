"use client";

import { useCommandCenterData } from "@/features/command-center/hooks/use-command-center-data";
import { CommandCenterScreen } from "@/features/command-center/command-center-screen";

export function CommandCenterLive() {
  const {
    data,
    kpis,
    executiveBrief,
    priorityActions,
    executiveTimeline,
    loading,
    error,
    reload,
    lastUpdated
  } = useCommandCenterData();

  return (
    <CommandCenterScreen
      {...data}
      error={error}
      executiveBrief={executiveBrief}
      executiveTimeline={executiveTimeline}
      kpis={kpis}
      lastUpdated={lastUpdated}
      loading={loading}
      priorityActions={priorityActions}
      reload={reload}
    />
  );
}
