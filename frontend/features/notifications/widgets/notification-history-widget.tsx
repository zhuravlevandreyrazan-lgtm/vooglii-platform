import Link from "next/link";
import { StatusBadge } from "@/shared/status";
import { localizeStatus, localizeWorkspaceLabel } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { NotificationHistoryItem } from "@/features/notifications/types";

export function NotificationHistoryWidget({
  history,
  loading = false,
  error = null
}: {
  history: NotificationHistoryItem[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={history.length === 0}
      emptyMessage="История уведомлений появится после загрузки событий доставки."
      error={error}
      loading={loading}
      subtitle="Последние отправки"
      title="История уведомлений"
    >
      <div className="space-y-3">
        {history.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-semibold">{item.title}</p>
                <p className="mt-1 text-sm text-[var(--ink-soft)]">{item.target}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone="neutral">{item.channel}</StatusBadge>
                <StatusBadge tone={item.status === "sent" ? "healthy" : item.status === "failed" ? "risk" : "watch"}>
                  {localizeStatus(item.status)}
                </StatusBadge>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-[var(--ink-soft)]">
              <span>{item.time}</span>
              <span>{item.relatedWorkspace ? localizeWorkspaceLabel(item.relatedWorkspace) : "Нет данных"}</span>
              {item.organizationName || item.cabinetName ? <span>{[item.organizationName, item.cabinetName].filter(Boolean).join(" • ")}</span> : null}
            </div>
            {item.error ? <p className="mt-3 text-sm leading-6 text-[var(--danger)]">{item.error}</p> : null}
            {item.deepLink ? (
              <Link className="mt-3 inline-flex text-sm font-semibold text-[var(--accent-strong)]" href={item.deepLink}>
                Открыть связанный раздел
              </Link>
            ) : null}
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
