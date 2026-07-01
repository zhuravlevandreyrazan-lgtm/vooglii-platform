"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/features/auth";
import { hasAnyPermission } from "@/features/auth/rbac";
import { cn } from "@/shared/lib/cn";

const SETTINGS_LINKS = [
  { href: "/settings/readiness", label: "Готовность", requiredPermissions: ["settings:manage"] as const },
  { href: "/settings/profile", label: "Профиль", requiredPermissions: ["dashboard:view"] as const },
  { href: "/settings/wb-cabinet", label: "Кабинет WB", requiredPermissions: ["settings:manage"] as const },
  { href: "/team", label: "Команда", requiredPermissions: ["users:view"] as const },
  { href: "/notifications", label: "Уведомления", requiredPermissions: ["dashboard:view"] as const }
];

export function SettingsNav() {
  const pathname = usePathname();
  const { permissions } = useAuth();
  const visibleLinks = SETTINGS_LINKS.filter((item) => hasAnyPermission(permissions, [...item.requiredPermissions]));

  return (
    <div className="flex flex-wrap gap-3">
      {visibleLinks.map((item) => {
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
