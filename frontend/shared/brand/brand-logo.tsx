import Image from "next/image";
import { cn } from "@/shared/lib/cn";

export function BrandLogo({
  compact = false,
  className,
  priority = false
}: {
  compact?: boolean;
  className?: string;
  priority?: boolean;
}) {
  if (compact) {
    return (
      <Image
        alt="VOOGLII"
        className={cn("h-12 w-12 rounded-[18px]", className)}
        height={48}
        priority={priority}
        src="/brand/logo-icon.svg"
        width={48}
      />
    );
  }

  return (
    <Image
      alt="VOOGLII"
      className={cn("h-14 w-auto", className)}
      height={56}
      priority={priority}
      src="/brand/logo-full.svg"
      width={184}
    />
  );
}
