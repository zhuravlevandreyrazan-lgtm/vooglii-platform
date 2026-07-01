"use client";

import Link from "next/link";
import { cn } from "@/shared/lib/cn";

export function OpenAutomationLink({
  workspace,
  label = "Открыть в автоматизации",
  format,
  sku,
  className
}: {
  workspace: string;
  label?: string;
  format?: string;
  sku?: string;
  className?: string;
}) {
  const searchParams = new URLSearchParams();
  searchParams.set("workspace", workspace);
  if (format) {
    searchParams.set("format", format);
  }
  if (sku) {
    searchParams.set("sku", sku);
  }

  return (
    <Link
      className={cn(
        "inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]",
        className
      )}
      href={`/automation?${searchParams.toString()}`}
    >
      {label}
    </Link>
  );
}
