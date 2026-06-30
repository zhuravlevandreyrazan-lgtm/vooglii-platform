import Link from "next/link";
import { cn } from "@/shared/lib/cn";

export function SidebarItem({
  href,
  label,
  description,
  active
}: {
  href: string;
  label: string;
  description: string;
  active?: boolean;
}) {
  return (
    <Link
      className={cn(
        "group block rounded-3xl border px-4 py-3 transition",
        active
          ? "border-transparent bg-[var(--ink)] text-white shadow-[var(--shadow-soft)]"
          : "border-[var(--line)] bg-white/50 hover:bg-white"
      )}
      href={href}
    >
      <div className="text-sm font-semibold">{label}</div>
      <div
        className={cn(
          "mt-1 text-xs leading-5",
          active ? "text-white/75" : "text-[var(--ink-soft)]"
        )}
      >
        {description}
      </div>
    </Link>
  );
}
