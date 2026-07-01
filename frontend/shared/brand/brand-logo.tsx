import Image from "next/image";
import { cn } from "@/shared/lib/cn";

type BrandLogoVariant = "sidebar" | "icon" | "wordmark" | "full";
type BrandLogoSize = "sm" | "md" | "lg";

function BrandIcon({
  className,
  size = "md"
}: {
  className?: string;
  size?: BrandLogoSize;
}) {
  const iconSize = {
    sm: "h-9 w-9",
    md: "h-11 w-11",
    lg: "h-14 w-14"
  }[size];

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full border border-[color:rgba(217,119,69,0.16)] bg-[linear-gradient(180deg,#fff8f1_0%,#f6ede2_100%)] shadow-[0_10px_24px_rgba(217,119,69,0.12)]",
        iconSize,
        className
      )}
      aria-hidden="true"
    >
      <svg viewBox="0 0 48 48" className="h-[78%] w-[78%]" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="18" stroke="#D97745" strokeWidth="2.6" opacity="0.22" />
        <path d="M15 14.5L24.4 31.4L38 10.8" stroke="#D97745" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M30.8 10.8H38V18" stroke="#D97745" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

export function BrandLogo({
  compact = false,
  variant,
  size = "md",
  className,
  priority = false
}: {
  compact?: boolean;
  variant?: BrandLogoVariant;
  size?: BrandLogoSize;
  className?: string;
  priority?: boolean;
}) {
  const resolvedVariant = variant ?? (compact ? "icon" : "full");

  if (resolvedVariant === "icon") {
    return <BrandIcon className={className} size={size} />;
  }

  if (resolvedVariant === "wordmark") {
    return (
      <div className={cn("flex min-w-0 flex-col", className)}>
        <span className="text-[0.98rem] font-semibold uppercase tracking-[0.28em] text-[var(--ink)]">
          VOOGLII
        </span>
      </div>
    );
  }

  if (resolvedVariant === "sidebar") {
    const iconClass = size === "lg" ? "gap-4" : "gap-3";
    return (
      <div className={cn("flex min-w-0 items-center", iconClass, className)}>
        <BrandIcon size={size === "sm" ? "sm" : "md"} />
        <div className="min-w-0">
          <div className="text-base font-semibold uppercase tracking-[0.24em] text-[var(--ink)]">
            VOOGLII
          </div>
          <div className="mt-1 max-w-[160px] text-[11px] leading-5 text-[var(--ink-soft)]">
            Платформа управления бизнесом на Wildberries
          </div>
        </div>
      </div>
    );
  }

  return (
    <Image
      alt="VOOGLII"
      className={cn(
        size === "sm" ? "h-10 w-auto" : size === "lg" ? "h-16 w-auto" : "h-14 w-auto",
        className
      )}
      height={56}
      priority={priority}
      src="/brand/vooglii-logo-full.png"
      width={184}
    />
  );
}
