import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";
import type { StatusTone } from "@/types/platform";

const toneClasses: Record<StatusTone, string> = {
  healthy: "border border-[color:rgba(78,140,102,0.18)] bg-[color:rgba(78,140,102,0.10)] text-[var(--success)]",
  watch: "border border-[color:rgba(217,164,65,0.18)] bg-[color:rgba(217,164,65,0.14)] text-[var(--warning)]",
  risk: "border border-[color:rgba(199,92,92,0.16)] bg-[color:rgba(199,92,92,0.10)] text-[var(--danger)]",
  neutral: "border border-[color:rgba(232,224,213,0.95)] bg-[color:rgba(255,253,252,0.92)] text-[var(--ink-soft)]",
  accent: "border border-[color:rgba(217,119,69,0.16)] bg-[color:rgba(217,119,69,0.12)] text-[var(--accent-strong)]"
};

export function StatusBadge({
  tone,
  children,
  className
}: {
  tone: StatusTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center justify-center rounded-full px-2.5 py-1 text-center text-[11px] font-semibold tracking-[0.08em] leading-4",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
