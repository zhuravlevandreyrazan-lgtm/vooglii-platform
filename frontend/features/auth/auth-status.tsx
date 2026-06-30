"use client";

import { RuntimeBadge } from "@/shared/api";
import { StatusBadge } from "@/shared/status";
import { useAuth } from "@/features/auth/auth-provider";

export function AuthStatus() {
  const { authenticated, cabinet, organization, user, diagnostics, loading } = useAuth();

  if (loading) {
    return <StatusBadge tone="neutral">Loading session</StatusBadge>;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge tone={authenticated ? "healthy" : "watch"}>
        {authenticated ? "Authenticated" : "Guest"}
      </StatusBadge>
      {organization ? <StatusBadge tone="neutral">{organization.name}</StatusBadge> : null}
      {cabinet ? (
        <StatusBadge tone={cabinet.connected ? "healthy" : "watch"}>
          Cabinet {cabinet.connected ? "connected" : "disconnected"}
        </StatusBadge>
      ) : null}
      {user ? <StatusBadge tone="accent">{user.role}</StatusBadge> : null}
      <RuntimeBadge diagnostics={diagnostics} />
    </div>
  );
}
