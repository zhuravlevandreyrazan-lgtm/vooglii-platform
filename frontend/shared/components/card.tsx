import type { HTMLAttributes } from "react";
import { cn } from "@/shared/lib/cn";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  surface?: "default" | "muted" | "accent";
};

export function Card({
  className,
  surface = "default",
  children,
  ...props
}: CardProps) {
  const surfaceClass = {
    default: "bg-[var(--panel)] border-[var(--line)]",
    muted: "bg-[var(--panel-strong)] border-[var(--line)]",
    accent: "bg-[linear-gradient(135deg,#1f2937_0%,#0f172a_55%,#172554_100%)] text-white border-transparent"
  };

  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] border p-5 shadow-[var(--shadow-soft)]",
        surfaceClass[surface],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
