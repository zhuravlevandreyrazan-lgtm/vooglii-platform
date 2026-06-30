import Link from "next/link";
import { Button } from "@/shared/components/button";
import { SeverityBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { NotificationRuleItem } from "@/features/notifications/types";

export function NotificationRulesWidget({
  rules,
  pendingAction = false,
  onToggleRule,
  loading = false,
  error = null
}: {
  rules: NotificationRuleItem[];
  pendingAction?: boolean;
  onToggleRule: (ruleId: string, enabled: boolean) => Promise<void>;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={rules.length === 0}
      emptyMessage="Notification rules will appear here when rule metadata is available."
      error={error}
      loading={loading}
      subtitle="Routing rules"
      title="Rules"
    >
      <div className="space-y-3">
        {rules.map((item) => (
          <div key={item.id} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-base font-semibold">{item.name}</p>
                <p className="mt-1 text-sm text-[var(--ink-soft)]">{item.channel} • {item.schedule}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone={item.enabled ? "healthy" : "watch"}>{item.enabled ? "Enabled" : "Muted"}</StatusBadge>
                <SeverityBadge severity={item.severity} />
              </div>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Trigger</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.trigger}</p>
              </div>
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Owner</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.owner}</p>
                {item.organizationName || item.cabinetName ? (
                  <p className="mt-2 text-xs text-[var(--ink-soft)]">
                    {[item.organizationName, item.cabinetName].filter(Boolean).join(" • ")}
                  </p>
                ) : null}
              </div>
              <div className="rounded-[18px] bg-[var(--panel-strong)] p-3 text-sm">
                <p className="font-semibold">Last triggered</p>
                <p className="mt-1 text-[var(--ink-soft)]">{item.lastTriggeredAt ?? "Not triggered yet"}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button disabled={pendingAction} onClick={() => void onToggleRule(item.id, !item.enabled)} variant={item.enabled ? "ghost" : "secondary"}>
                {item.enabled ? "Mute Rule" : "Enable Rule"}
              </Button>
              {item.deepLink ? (
                <Link className="inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]" href={item.deepLink}>
                  Open workspace
                </Link>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
