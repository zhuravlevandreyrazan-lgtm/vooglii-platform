"use client";

import { NotificationsScreen } from "@/features/notifications/notifications-screen";
import { useNotificationsData } from "@/features/notifications/hooks/use-notifications-data";
import { useWorkspaceContext } from "@/shared/workspace-context";

export function NotificationsLive() {
  const workspace = useWorkspaceContext();
  const {
    data,
    loading,
    error,
    actionMessage,
    pendingAction,
    lastTestResult,
    lastUpdated,
    diagnostics,
    sendTest,
    toggleRule
  } = useNotificationsData();

  return (
    <NotificationsScreen
      actionMessage={actionMessage}
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastTestResult={lastTestResult}
      lastUpdated={lastUpdated}
      loading={loading}
      onSendTest={sendTest}
      onToggleRule={toggleRule}
      pendingAction={pendingAction}
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
