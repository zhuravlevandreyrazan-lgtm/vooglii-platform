import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { NotificationChannelItem, NotificationTestResult } from "@/features/notifications/types";

export function TestNotificationWidget({
  channels,
  lastResult,
  pendingAction = false,
  onSendTest,
  loading = false,
  error = null
}: {
  channels: NotificationChannelItem[];
  lastResult: NotificationTestResult | null;
  pendingAction?: boolean;
  onSendTest: (channel: NotificationChannelItem["type"]) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="Safe delivery simulation" title="Test Notification">
      <div className="space-y-4">
        <p className="text-sm leading-7 text-[var(--ink-soft)]">
          Test notifications use fake delivery results in dev and demo mode. No real Telegram,
          email, or webhook delivery happens from the frontend.
        </p>
        <div className="flex flex-wrap gap-3">
          {channels.map((item) => (
            <Button
              key={item.id}
              disabled={pendingAction}
              onClick={() => void onSendTest(item.type)}
              variant={item.type === "in_app" ? "secondary" : "ghost"}
            >
              Send Test {item.type}
            </Button>
          ))}
        </div>
        {lastResult ? (
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone="neutral">{lastResult.channel}</StatusBadge>
              <StatusBadge tone={lastResult.status === "sent" ? "healthy" : "watch"}>{lastResult.status}</StatusBadge>
              {lastResult.organizationName ? <StatusBadge tone="neutral">{lastResult.organizationName}</StatusBadge> : null}
              {lastResult.cabinetName ? <StatusBadge tone="neutral">{lastResult.cabinetName}</StatusBadge> : null}
            </div>
            <p className="mt-3 text-sm font-semibold">{lastResult.target}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{lastResult.message}</p>
          </div>
        ) : null}
      </div>
    </WidgetCard>
  );
}
