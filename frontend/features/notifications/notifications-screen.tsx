"use client";

import { useAuth } from "@/features/auth";
import { NotificationChannelsWidget } from "@/features/notifications/widgets/notification-channels-widget";
import { NotificationHistoryWidget } from "@/features/notifications/widgets/notification-history-widget";
import { NotificationsOverviewWidget } from "@/features/notifications/widgets/notifications-overview-widget";
import { NotificationRulesWidget } from "@/features/notifications/widgets/notification-rules-widget";
import { TestNotificationWidget } from "@/features/notifications/widgets/test-notification-widget";
import type { NotificationChannelItem, NotificationsSnapshot } from "@/features/notifications/types";
import { RuntimeBadge } from "@/shared/api";
import { Alert } from "@/shared/components/alert";
import { PageHeader } from "@/shared/layout";
import { StatusBadge } from "@/shared/status";
import type { NotificationTestResult } from "@/features/notifications/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function NotificationsScreen({
  data,
  diagnostics,
  loading = false,
  error = null,
  actionMessage = null,
  lastTestResult = null,
  pendingAction = false,
  lastUpdated,
  onSendTest,
  onToggleRule,
  workspaceContext
}: {
  data: NotificationsSnapshot;
  diagnostics?: WorkspaceDiagnostics;
  loading?: boolean;
  error?: string | null;
  actionMessage?: string | null;
  lastTestResult?: NotificationTestResult | null;
  pendingAction?: boolean;
  lastUpdated?: string | null;
  onSendTest: (channel: NotificationChannelItem["type"]) => Promise<void>;
  onToggleRule: (ruleId: string, enabled: boolean) => Promise<void>;
  workspaceContext?: {
    organizationId?: string | null;
    organization?: string | null;
    cabinetId?: string | null;
    cabinet?: string | null;
    mode?: string | null;
  };
}) {
  const { organization, user } = useAuth();

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Notifications"]}
        subtitle="A single hub for channels, routing rules, history, test delivery, and future backend-only Telegram, email, webhook, and scheduled report delivery."
        title="Notifications Hub"
        updatedAt={lastUpdated ?? undefined}
      />

      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge tone="accent">Unread {data.unreadCount}</StatusBadge>
        {organization ? <StatusBadge tone="neutral">{organization.name}</StatusBadge> : null}
        {user ? <StatusBadge tone="neutral">{user.name}</StatusBadge> : null}
        {actionMessage ? <StatusBadge tone="neutral">{actionMessage}</StatusBadge> : null}
      </div>

      <RuntimeBadge context={workspaceContext} diagnostics={diagnostics} />

      {diagnostics?.validationStatus === "fallback" ? (
        <Alert
          detail="Using fallback data. Notification backend responses are unavailable or invalid, but the safe hub remains usable."
          title="Fallback notifications snapshot active"
          tone="watch"
        />
      ) : null}

      <NotificationsOverviewWidget
        error={error}
        loading={loading}
        overview={data.overview}
        quickStats={data.quickStats}
      />

      <NotificationChannelsWidget
        channels={data.channels}
        error={error}
        loading={loading}
        onSendTest={onSendTest}
        pendingAction={pendingAction}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <NotificationRulesWidget
          error={error}
          loading={loading}
          onToggleRule={onToggleRule}
          pendingAction={pendingAction}
          rules={data.rules}
        />
        <TestNotificationWidget
          channels={data.channels}
          error={error}
          lastResult={lastTestResult}
          loading={loading}
          onSendTest={onSendTest}
          pendingAction={pendingAction}
        />
      </div>

      <NotificationHistoryWidget error={error} history={data.history} loading={loading} />
    </div>
  );
}
