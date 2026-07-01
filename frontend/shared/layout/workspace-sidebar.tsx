"use client";

import Link from "next/link";
import { PanelLeftClose } from "lucide-react";
import { useAuth } from "@/features/auth";
import { hasAnyPermission } from "@/features/auth/rbac";
import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { theme } from "@/shared/theme";
import { cn } from "@/shared/lib/cn";
import { workspaceNavigation } from "@/shared/layout/platform-shell.config";
import { useWorkspaceContext } from "@/shared/workspace-context";

function isActivePath(pathname: string, href: string) {
  return pathname === href;
}

export function WorkspaceSidebar({
  pathname,
  collapsed,
  mobileOpen,
  onClose,
  onToggleCollapsed
}: {
  pathname: string;
  collapsed: boolean;
  mobileOpen: boolean;
  onClose: () => void;
  onToggleCollapsed: () => void;
}) {
  const workspace = useWorkspaceContext();
  const { permissions } = useAuth();
  const visibleNavigation = workspaceNavigation.filter((item) => hasAnyPermission(permissions, item.requiredPermissions));

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 border-r border-[var(--line)] bg-[color:rgba(255,253,248,0.96)] p-5 backdrop-blur transition-transform duration-200 lg:static lg:translate-x-0",
        collapsed ? "w-[108px]" : "w-[300px]",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-start justify-between gap-3">
          <Link className="inline-flex items-center gap-3" href="/executive">
            <div className="flex h-12 w-12 items-center justify-center rounded-[18px] bg-[var(--ink)] text-lg font-semibold text-white">
              V
            </div>
            {!collapsed ? (
              <div>
                <div className="text-lg font-semibold">{theme.brand.name}</div>
                <div className="mt-1 max-w-[160px] text-xs leading-5 text-[var(--ink-soft)]">
                  {theme.brand.tagline}
                </div>
              </div>
            ) : null}
          </Link>
          <div className="flex items-center gap-2">
            <Button aria-label="Collapse sidebar" className="hidden lg:inline-flex" variant="ghost" onClick={onToggleCollapsed}>
              <PanelLeftClose size={16} className={cn(collapsed ? "rotate-180" : "")} />
            </Button>
            <Button aria-label="Close sidebar" className="lg:hidden" variant="ghost" onClick={onClose}>
              <PanelLeftClose size={16} />
            </Button>
          </div>
        </div>

        {!collapsed ? (
          <div className="mt-8 rounded-[28px] border border-[var(--line)] bg-[linear-gradient(180deg,#fff8ed_0%,#f6efe2_100%)] p-4 shadow-[var(--shadow-soft)]">
            <StatusBadge tone="accent">DEV</StatusBadge>
            <h2 className="mt-4 text-xl font-semibold tracking-[-0.04em]">Commercial platform shell</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
              Shared workspace architecture for leadership, finance, operations, and future AI modules.
            </p>
            <div className="mt-4 space-y-3 rounded-[22px] border border-[var(--line)] bg-white/70 p-4 text-sm">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Organization</p>
                <p className="mt-1 font-semibold">{workspace.organization?.name ?? "Loading organization"}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Cabinet</p>
                <p className="mt-1 font-semibold">{workspace.cabinet?.name ?? "Loading cabinet"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone={workspace.cabinet?.connected ? "healthy" : "watch"}>
                  {workspace.cabinet?.connected ? "Connected" : "Disconnected"}
                </StatusBadge>
                {workspace.cabinet?.health ? <StatusBadge tone="neutral">{workspace.cabinet.health}</StatusBadge> : null}
              </div>
            </div>
          </div>
        ) : null}

        <nav className="mt-8 flex-1 space-y-2 overflow-y-auto pr-1" aria-label="Workspace navigation">
          {visibleNavigation.map((item) => {
            const active = isActivePath(pathname, item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-3xl border px-4 py-3 outline-none transition focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2",
                  active
                    ? "border-transparent bg-[var(--ink)] text-white shadow-[var(--shadow-soft)]"
                    : "border-[var(--line)] bg-white/55 hover:bg-white"
                )}
                href={item.href}
                onClick={onClose}
              >
                <div className={cn("flex h-10 w-10 items-center justify-center rounded-2xl", active ? "bg-white/10" : "bg-[var(--panel-strong)]")}>
                  <Icon size={18} />
                </div>
                {!collapsed ? (
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{item.label}</div>
                    <div className={cn("mt-1 text-xs leading-5", active ? "text-white/75" : "text-[var(--ink-soft)]")}>
                      {item.description}
                    </div>
                  </div>
                ) : null}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
