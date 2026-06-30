"use client";

import Link from "next/link";
import { Bell, Menu, RefreshCcw, Search, UserCircle2 } from "lucide-react";
import { useAuth } from "@/features/auth";
import { useNotificationSummary } from "@/features/notifications/hooks/use-notification-summary";
import { useDemoMode } from "@/shared/demo/demo-provider";
import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/status";
import { useWorkspaceContext } from "@/shared/workspace-context";

export function WorkspaceTopBar({
  title,
  breadcrumb,
  lastUpdated,
  onOpenSidebar
}: {
  title: string;
  breadcrumb: string[];
  lastUpdated?: string;
  onOpenSidebar: () => void;
}) {
  const { enabled, toggleDemoMode } = useDemoMode();
  const { cabinet, organization, user, loading } = useAuth();
  const workspace = useWorkspaceContext();
  const notificationSummary = useNotificationSummary();
  const clockLabel = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date());
  const initials = (user?.name ?? "User")
    .split(" ")
    .map((part) => part[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--line)] bg-[color:rgba(244,239,231,0.82)] px-4 py-4 backdrop-blur lg:px-8">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center gap-3">
          <Button aria-label="Open sidebar" className="lg:hidden" variant="ghost" onClick={onOpenSidebar}>
            <Menu size={16} />
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
              {breadcrumb.map((item, index) => (
                <span key={`${item}-${index}`} className="inline-flex items-center gap-2">
                  {index > 0 ? <span className="text-[var(--line)]">/</span> : null}
                  <span>{item}</span>
                </span>
              ))}
            </div>
            <div className="mt-1 text-2xl font-semibold tracking-[-0.04em]">{title}</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex min-w-[220px] items-center gap-2 rounded-full border border-[var(--line)] bg-white/60 px-4 py-2.5 shadow-[var(--shadow-soft)]">
            <Search size={16} className="text-[var(--ink-soft)]" />
            <span className="text-sm text-[var(--ink-soft)]">Search workspace, report, or insight</span>
          </div>
          {lastUpdated ? <StatusBadge tone="neutral">Updated {lastUpdated}</StatusBadge> : null}
          {enabled ? <StatusBadge tone="accent">DEMO MODE</StatusBadge> : null}
          <StatusBadge tone="accent">DEV</StatusBadge>
          {workspace.organization ? <StatusBadge tone="neutral">{workspace.organization.name}</StatusBadge> : null}
          {workspace.cabinet ? (
            <StatusBadge tone={workspace.cabinet.connected ? "healthy" : "watch"}>
              Cabinet {workspace.cabinet.connected ? "connected" : "disconnected"}
            </StatusBadge>
          ) : null}
          {!loading && cabinet && !cabinet.connected ? (
            <StatusBadge tone="watch">Connect WB cabinet for live sync</StatusBadge>
          ) : null}
          {process.env.NODE_ENV === "development" ? (
            <div className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] bg-white/75 p-1 shadow-[var(--shadow-soft)]">
              <button
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${!enabled ? "bg-[var(--ink)] text-white" : "text-[var(--ink-soft)] hover:text-[var(--ink)]"}`}
                onClick={() => enabled && toggleDemoMode()}
                type="button"
              >
                Live
              </button>
              <button
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${enabled ? "bg-[var(--accent)] text-white" : "text-[var(--ink-soft)] hover:text-[var(--ink)]"}`}
                onClick={() => !enabled && toggleDemoMode()}
                type="button"
              >
                Demo
              </button>
            </div>
          ) : null}
          <select
            aria-label="Select organization"
            className="rounded-full border border-[var(--line)] bg-white/75 px-3 py-2 text-sm outline-none"
            disabled={workspace.loading || workspace.organizations.length === 0}
            onChange={(event) => {
              void workspace.selectOrganization(event.target.value);
            }}
            value={workspace.organization?.id ?? ""}
          >
            {workspace.organizations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Select WB cabinet"
            className="rounded-full border border-[var(--line)] bg-white/75 px-3 py-2 text-sm outline-none"
            disabled={workspace.loading || workspace.cabinets.length === 0}
            onChange={(event) => {
              void workspace.selectCabinet(event.target.value);
            }}
            value={workspace.cabinet?.id ?? ""}
          >
            {workspace.cabinets.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <StatusBadge tone="healthy">{clockLabel}</StatusBadge>
          <Button aria-label="Reload placeholder" variant="ghost">
            <RefreshCcw size={16} />
          </Button>
          <Link
            aria-label="Notifications"
            className="relative inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-white/60 px-3 py-2 text-sm font-semibold transition hover:bg-white"
            href="/notifications"
          >
            <Bell size={16} />
            {notificationSummary.unreadCount > 0 ? (
              <span className="inline-flex min-w-6 items-center justify-center rounded-full bg-[var(--accent)] px-2 py-0.5 text-xs font-semibold text-white">
                {notificationSummary.unreadCount}
              </span>
            ) : null}
          </Link>
          <div className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-white/60 px-3 py-2 shadow-[var(--shadow-soft)]">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--ink)] text-xs font-semibold text-white">
              {loading ? <UserCircle2 size={14} /> : initials}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{user?.name ?? "User"}</div>
              <div className="truncate text-xs text-[var(--ink-soft)]">{workspace.organization?.name ?? organization?.name ?? "Loading organization"}</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
