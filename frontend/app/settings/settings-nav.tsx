"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/shared/lib/cn";

const SETTINGS_LINKS = [
  { href: "/settings/readiness", label: "Readiness" },
  { href: "/settings/profile", label: "Profile" },
  { href: "/settings/wb-cabinet", label: "WB Cabinet" },
  { href: "/notifications", label: "Notifications" }
];

export function SettingsNav() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-3">
      {SETTINGS_LINKS.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            className={cn(
              "inline-flex rounded-full border px-4 py-2.5 text-sm font-semibold transition",
              active
                ? "border-transparent bg-[var(--ink)] text-white shadow-[var(--shadow-soft)]"
                : "border-[var(--line)] bg-white hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            )}
            href={item.href}
          >
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}
