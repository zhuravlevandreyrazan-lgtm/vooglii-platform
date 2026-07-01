import type { ReactNode } from "react";
import { Card } from "@/shared/components/card";
import { StatusBadge } from "@/shared/components/status-badge";
import { cn } from "@/shared/lib/cn";
import { humanizeErrorMessage } from "@/shared/ui/status-labels";
import type { WidgetCardProps } from "@/shared/widgets/types";

function renderStatus(status: WidgetCardProps["status"]): ReactNode {
  if (!status) {
    return null;
  }
  if (typeof status === "object" && "label" in status && "tone" in status) {
    return <StatusBadge tone={status.tone}>{status.label}</StatusBadge>;
  }
  return status;
}

function LoadingState() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-3.5 w-2/5 rounded-full bg-[var(--panel-strong)]" />
      <div className="h-3.5 w-full rounded-full bg-[var(--panel-strong)]" />
      <div className="h-3.5 w-3/4 rounded-full bg-[var(--panel-strong)]" />
      <div className="h-20 rounded-[18px] bg-[var(--panel-strong)]" />
    </div>
  );
}

function MessageState({
  title,
  message,
  tone
}: {
  title: string;
  message: string;
  tone: "error" | "empty";
}) {
  const toneClass =
    tone === "error"
      ? "border-[color:rgba(199,92,92,0.18)] bg-[color:rgba(199,92,92,0.06)] text-[var(--danger)]"
      : "border-[var(--line)] bg-[linear-gradient(180deg,#fffdfc_0%,#fbf6ef_100%)] text-[var(--ink-soft)]";

  return (
    <div className={cn("rounded-[20px] border p-3.5", toneClass)}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-2 text-sm leading-6">{message}</p>
    </div>
  );
}

export function WidgetCard({
  title,
  subtitle,
  status,
  children,
  actions,
  updatedAt,
  loading = false,
  error,
  empty = false,
  emptyMessage = "Данные появятся после первой синхронизации.",
  className,
  ...props
}: WidgetCardProps) {
  let content: ReactNode = children;

  if (loading) {
    content = <LoadingState />;
  } else if (error) {
    content = (
      <MessageState
        message={humanizeErrorMessage(error)}
        title="Не удалось загрузить данные"
        tone="error"
      />
    );
  } else if (empty) {
    content = <MessageState message={emptyMessage} title="Ожидаем данные" tone="empty" />;
  }

  return (
    <Card className={className} {...props}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
            {title}
          </p>
          {subtitle ? (
            <h2 className="mt-1 text-[1.55rem] font-semibold tracking-[-0.04em]">{subtitle}</h2>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {actions}
          {renderStatus(status)}
        </div>
      </div>

      <div className="mt-5">{content}</div>

      {updatedAt ? (
        <div className="mt-4 text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--ink-soft)]">
          Обновлено {updatedAt}
        </div>
      ) : null}
    </Card>
  );
}
