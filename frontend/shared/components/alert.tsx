import { AlertTriangle } from "lucide-react";
import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
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
    <Card className="flex gap-4">
      <div className="mt-1 rounded-2xl bg-[var(--panel-strong)] p-3 text-[var(--accent)]">
        <AlertTriangle size={18} />
      </div>
      <div className="space-y-2">
        <StatusBadge tone={tone}>{tone}</StatusBadge>
        <div>
          <h3 className="text-base font-semibold">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">{detail}</p>
        </div>
      </div>
    </Card>
  );
}
