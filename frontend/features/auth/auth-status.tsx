"use client";

import { useAuth } from "@/features/auth/auth-provider";
import { RuntimeBadge } from "@/shared/api";
import { StatusBadge } from "@/shared/status";
import { localizeRoleLabel } from "@/shared/ui/status-labels";

export function AuthStatus() {
  const { authenticated, cabinet, organization, user, diagnostics, loading } = useAuth();

  if (loading) {
    return <StatusBadge tone="neutral">Загружаем сессию</StatusBadge>;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <StatusBadge tone={authenticated ? "healthy" : "watch"}>
        {authenticated ? "Сессия активна" : "Гостевой режим"}
      </StatusBadge>
      {organization ? <StatusBadge tone="neutral">{organization.name}</StatusBadge> : null}
      {cabinet ? (
        <StatusBadge tone={cabinet.connected ? "healthy" : "watch"}>
          {cabinet.connected ? "Кабинет подключен" : "Кабинет не подключен"}
        </StatusBadge>
      ) : null}
      {user ? <StatusBadge tone="accent">{localizeRoleLabel(user.role)}</StatusBadge> : null}
      <RuntimeBadge diagnostics={diagnostics} />
    </div>
  );
}
