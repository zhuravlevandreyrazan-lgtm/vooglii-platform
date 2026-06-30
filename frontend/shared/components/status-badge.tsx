import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";
import type { StatusTone } from "@/types/platform";

const toneClasses: Record<StatusTone, string> = {
  healthy: "bg-[color:rgba(47,125,99,0.12)] text-[var(--success)]",
  watch: "bg-[color:rgba(176,122,24,0.14)] text-[var(--warning)]",
  risk: "bg-[color:rgba(184,69,69,0.12)] text-[var(--danger)]",
  neutral: "bg-[color:rgba(51,65,85,0.08)] text-[var(--ink-soft)]",
  accent: "bg-[color:rgba(208,104,63,0.12)] text-[var(--accent-strong)]"
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
        "inline-flex rounded-full px-3 py-1 text-xs font-semibold tracking-[0.12em] uppercase",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
