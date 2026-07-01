import { AlertTriangle } from "lucide-react";
import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
import { localizeStatus } from "@/shared/ui/status-labels";
import type { StatusTone } from "@/types/platform";

export function Alert({
  title,
  detail,
  tone
}: {
  title: string;
  detail: string;
  tone: StatusTone;
}) {
  return (
    <Card className="flex gap-3 rounded-[22px]">
      <div className="mt-0.5 rounded-2xl bg-[var(--panel-strong)] p-2.5 text-[var(--accent)]">
        <AlertTriangle size={16} />
      </div>
      <div className="space-y-2">
        <StatusBadge tone={tone}>{localizeStatus(tone)}</StatusBadge>
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">{detail}</p>
        </div>
      </div>
    </Card>
  );
}
