import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  icon?: ReactNode;
};

export function Button({
  className,
  variant = "primary",
  icon,
  children,
  ...props
}: ButtonProps) {
  const variants = {
    primary:
      "bg-[var(--ink)] text-white hover:bg-[color:rgba(15,23,42,0.9)] shadow-[var(--shadow-soft)]",
    secondary:
      "bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)] shadow-[var(--shadow-soft)]",
    ghost:
      "border border-[var(--line)] bg-white/60 text-[var(--ink)] hover:bg-white"
  };

  return (
    <button
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold transition",
        variants[variant],
        className
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
