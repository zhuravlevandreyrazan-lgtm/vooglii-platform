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
    accent: "bg-[linear-gradient(135deg,#fff6ee_0%,#f6ebdf_55%,#fdf7f1_100%)] text-[var(--ink)] border-[color:rgba(217,119,69,0.18)]"
  };

  return (
    <div
      className={cn(
        "rounded-[var(--radius-card)] border p-4 shadow-[var(--shadow-soft)] lg:p-5",
        surfaceClass[surface],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
