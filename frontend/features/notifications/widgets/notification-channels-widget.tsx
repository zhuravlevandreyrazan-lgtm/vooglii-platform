import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { NotificationChannelItem } from "@/features/notifications/types";

export function NotificationChannelsWidget({
  channels,
  pendingAction = false,
  onSendTest,
  loading = false,
  error = null
}: {
  channels: NotificationChannelItem[];
  pendingAction?: boolean;
  onSendTest: (channel: NotificationChannelItem["type"]) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={channels.length === 0}
      emptyMessage="Каналы уведомлений появятся здесь после загрузки настроек доставки."
      error={error}
      loading={loading}
      subtitle="Delivery channels"
      title="Channels"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {channels.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-base font-semibold">{item.type}</p>
              <StatusBadge tone={item.connected ? "healthy" : "watch"}>{item.status}</StatusBadge>
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-soft)]">Delivery health: {item.deliveryHealth}</p>
            <p className="mt-2 text-sm text-[var(--ink-soft)]">Last test: {item.lastTestAt ?? "Not tested yet"}</p>
            <p className="mt-2 text-sm text-[var(--ink-soft)]">{item.setupAction ?? "Setup action pending"}</p>
            <div className="mt-4">
              <Button disabled={pendingAction} onClick={() => void onSendTest(item.type)} variant="secondary">
                Send Test
              </Button>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
