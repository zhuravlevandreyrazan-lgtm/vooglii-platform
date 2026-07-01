"use client";

import type { PlatformRole, UserProfile } from "@/features/auth/types";
import type { UsersSnapshot } from "@/features/users/types";
import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/components/status-badge";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

function formatDate(value?: string | null) {
  if (!value) {
    return "n/a";
  }

  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function roleTone(role: PlatformRole) {
  if (role === "owner" || role === "admin") {
    return "accent" as const;
  }
  if (role === "manager" || role === "analyst") {
    return "healthy" as const;
  }
  return "neutral" as const;
}

export function TeamScreen({
  data,
  loading,
  error,
  canViewUsers,
  canManageUsers,
  pendingUserId,
  actionMessage,
  currentUserId,
  onRoleChange,
  onToggleUser
}: {
  data: UsersSnapshot | null;
  loading: boolean;
  error: string | null;
  canViewUsers: boolean;
  canManageUsers: boolean;
  pendingUserId: string | null;
  actionMessage: string | null;
  currentUserId: string | null;
  onRoleChange: (userId: string, role: PlatformRole) => void;
  onToggleUser: (userId: string, enabled: boolean) => void;
}) {
  if (!canViewUsers) {
    return (
      <WidgetCard subtitle="Users and audit access are restricted to elevated roles." title="Access denied">
        <p className="text-sm leading-7 text-[var(--ink-soft)]">
          This screen is wired to backend permission checks. Once real auth arrives, the same
          contracts can plug into session-backed identity without changing the page API.
        </p>
      </WidgetCard>
    );
  }

  const users = data?.users ?? [];
  const roles = data?.availableRoles ?? [];
  const auditEvents = data?.auditEvents ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Team"]}
        subtitle="Manage platform roles, review effective permissions, and track backend audit hooks for sensitive user lifecycle changes."
        title="Users / Team"
      />

      {actionMessage ? (
        <div className="rounded-[22px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink-soft)]">
          {actionMessage}
        </div>
      ) : null}

      <WidgetCard
        title="Directory"
        subtitle="Users and roles"
        loading={loading}
        error={error ?? undefined}
        empty={!loading && !error && users.length === 0}
        emptyMessage="No platform users are available in the current scaffold."
      >
        <div className="space-y-4">
          {users.map((user: UserProfile) => {
            const busy = pendingUserId === user.id;
            return (
              <div key={user.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-base font-semibold">{user.name}</p>
                      <StatusBadge tone={roleTone(user.role)}>{user.role}</StatusBadge>
                      <StatusBadge tone={user.enabled ? "healthy" : "watch"}>{user.enabled ? "Enabled" : "Disabled"}</StatusBadge>
                      {currentUserId === user.id ? <StatusBadge tone="neutral">Current actor</StatusBadge> : null}
                    </div>
                    <p className="text-sm text-[var(--ink-soft)]">{user.email}</p>
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                      Permissions: {user.permissions.join(", ")}
                    </p>
                    <div className="flex flex-wrap gap-4 text-xs text-[var(--ink-soft)]">
                      <span>Created {formatDate(user.createdAt)}</span>
                      <span>Last active {formatDate(user.lastActiveAt)}</span>
                      {user.deactivatedAt ? <span>Disabled {formatDate(user.deactivatedAt)}</span> : null}
                    </div>
                  </div>

                  <div className="flex flex-col gap-3 xl:min-w-[240px]">
                    <label className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                      Role
                    </label>
                    <select
                      className="rounded-2xl border border-[var(--line)] bg-white px-4 py-2.5 text-sm"
                      disabled={!canManageUsers || busy}
                      onChange={(event) => onRoleChange(user.id, event.target.value as PlatformRole)}
                      value={user.role}
                    >
                      {roles.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                    <Button
                      disabled={!canManageUsers || busy || currentUserId === user.id}
                      onClick={() => onToggleUser(user.id, !user.enabled)}
                      variant={user.enabled ? "ghost" : "secondary"}
                    >
                      {busy ? "Saving..." : user.enabled ? "Disable user" : "Enable user"}
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </WidgetCard>

      <WidgetCard
        title="Audit"
        subtitle="Recent RBAC events"
        loading={loading}
        error={error ?? undefined}
        empty={!loading && !error && auditEvents.length === 0}
        emptyMessage="No RBAC events have been recorded yet."
      >
        <div className="space-y-3">
          {auditEvents.slice(0, 12).map((event) => (
            <div key={event.id} className="rounded-[20px] border border-[var(--line)] bg-white/70 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone={event.outcome === "denied" ? "watch" : "neutral"}>{event.outcome}</StatusBadge>
                <p className="text-sm font-semibold">{event.event}</p>
              </div>
              <p className="mt-2 text-sm text-[var(--ink-soft)]">
                Actor: {event.actorId}
                {event.targetId ? ` -> Target: ${event.targetId}` : ""}
              </p>
              {event.detail ? <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{event.detail}</p> : null}
              <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[var(--ink-soft)]">{formatDate(event.createdAt)}</p>
            </div>
          ))}
        </div>
      </WidgetCard>
    </div>
  );
}
