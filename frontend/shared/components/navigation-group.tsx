import { SidebarItem } from "@/shared/components/sidebar-item";
import type { NavItem } from "@/types/platform";

export function NavigationGroup({
  title,
  items,
  activePath
}: {
  title: string;
  items: NavItem[];
  activePath: string;
}) {
  return (
    <div className="space-y-3">
      <p className="px-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
        {title}
      </p>
      <div className="space-y-2">
        {items.map((item) => (
          <SidebarItem
            key={item.key}
            active={activePath === item.href}
            description={item.description}
            href={item.href}
            label={item.label}
          />
        ))}
      </div>
    </div>
  );
}
