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
        className={cn("h-10 w-auto", className)}
        height={40}
        priority={priority}
        src="/brand/vooglii-logo-full.png"
        width={131}
      />
    );
  }

  return (
    <Image
      alt="VOOGLII"
      className={cn("h-14 w-auto", className)}
      height={56}
      priority={priority}
      src="/brand/vooglii-logo-full.png"
      width={184}
    />
  );
}
