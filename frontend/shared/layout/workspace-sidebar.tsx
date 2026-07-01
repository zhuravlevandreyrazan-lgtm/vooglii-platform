"use client";

import Link from "next/link";
import { PanelLeftClose } from "lucide-react";
import { useAuth } from "@/features/auth";
import { hasAnyPermission } from "@/features/auth/rbac";
import { BrandLogo } from "@/shared/brand/brand-logo";
import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { cn } from "@/shared/lib/cn";
import { workspaceNavigation } from "@/shared/layout/platform-shell.config";
import { localizeStatus } from "@/shared/ui/status-labels";
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
        "fixed inset-y-0 left-0 z-40 border-r border-[var(--line)] bg-[color:rgba(255,253,252,0.97)] p-4 backdrop-blur transition-transform duration-200 lg:static lg:translate-x-0",
        collapsed ? "w-[96px]" : "w-[292px]",
        mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-start justify-between gap-3">
          <Link className="min-w-0 flex-1" href="/executive">
            <BrandLogo variant={collapsed ? "icon" : "sidebar"} priority size={collapsed ? "sm" : "md"} />
          </Link>
          <div className="flex items-center gap-2">
            <Button aria-label="Свернуть меню" className="hidden h-10 w-10 lg:inline-flex" variant="ghost" onClick={onToggleCollapsed}>
              <PanelLeftClose size={16} className={cn(collapsed ? "rotate-180" : "")} />
            </Button>
            <Button aria-label="Закрыть меню" className="h-10 w-10 lg:hidden" variant="ghost" onClick={onClose}>
              <PanelLeftClose size={16} />
            </Button>
          </div>
        </div>

        {!collapsed ? (
          <div className="mt-6 rounded-[24px] border border-[var(--line)] bg-[linear-gradient(180deg,#fffaf4_0%,#f6eee4_100%)] p-4 shadow-[var(--shadow-soft)]">
            <div className="flex items-center justify-between gap-3">
              <StatusBadge tone="accent">Панель продавца</StatusBadge>
              <StatusBadge tone={workspace.cabinet?.connected ? "healthy" : "watch"}>
                {workspace.cabinet?.connected ? "Подключен" : "Не подключен"}
              </StatusBadge>
            </div>
            <h2 className="mt-4 text-lg font-semibold tracking-[-0.03em]">Единый центр управления</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
              Продажи, финансы, реклама и остатки в одном рабочем пространстве.
            </p>
            <div className="mt-4 grid gap-3 rounded-[20px] border border-[var(--line)] bg-white/76 p-3 text-sm">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Организация</p>
                <p className="mt-1 font-semibold">{workspace.organization?.name ?? "Загрузка организации"}</p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Кабинет</p>
                <p className="mt-1 font-semibold">{workspace.cabinet?.name ?? "Загрузка кабинета"}</p>
              </div>
              {workspace.cabinet?.health ? (
                <div className="flex flex-wrap gap-2">
                  <StatusBadge tone="neutral">{localizeStatus(workspace.cabinet.health)}</StatusBadge>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        <nav className="mt-6 flex-1 space-y-2 overflow-y-auto pr-1" aria-label="Навигация по платформе">
          {visibleNavigation.map((item) => {
            const active = isActivePath(pathname, item.href);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-[22px] border px-3 py-2.5 outline-none transition focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2",
                  active
                    ? "border-[color:rgba(217,119,69,0.18)] bg-[linear-gradient(135deg,#fff5ec_0%,#f9ecdf_100%)] text-[var(--ink)] shadow-[var(--shadow-soft)]"
                    : "border-[var(--line)] bg-white/74 hover:border-[color:rgba(217,119,69,0.16)] hover:bg-white"
                )}
                href={item.href}
                onClick={onClose}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl",
                    active ? "bg-[color:rgba(217,119,69,0.12)] text-[var(--accent-strong)]" : "bg-[var(--panel-strong)]"
                  )}
                >
                  <Icon size={17} />
                </div>
                {!collapsed ? (
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{item.label}</div>
                    <div className="mt-1 max-w-[182px] text-[12px] leading-5 text-[var(--ink-soft)]">
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
