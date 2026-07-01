"use client";

import type { PlatformRole, UserProfile } from "@/features/auth/types";
import type { UsersSnapshot } from "@/features/users/types";
import { Button } from "@/shared/components/button";
import { StatusBadge } from "@/shared/components/status-badge";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

function formatDate(value?: string | null) {
  if (!value) {
    return "нет данных";
  }

  return new Intl.DateTimeFormat("ru-RU", {
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
      <WidgetCard subtitle="Просмотр пользователей и журнала доступен не всем ролям." title="Доступ ограничен">
        <p className="text-sm leading-7 text-[var(--ink-soft)]">
          Страница уже подключена к backend-проверкам прав. Когда появится полноценная авторизация,
          этот же контракт продолжит работать без изменения API страницы.
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
        breadcrumb={["Платформа", "Команда"]}
        subtitle="Пользователи, роли, права доступа и журнал чувствительных изменений."
        title="Команда"
      />

      {actionMessage ? (
        <div className="rounded-[22px] border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--ink-soft)]">
          {actionMessage}
        </div>
      ) : null}

      <WidgetCard
        title="Directory"
        subtitle="Пользователи и роли"
        loading={loading}
        error={error ?? undefined}
        empty={!loading && !error && users.length === 0}
        emptyMessage="Список пользователей пока пуст."
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
                      <StatusBadge tone={user.enabled ? "healthy" : "watch"}>{user.enabled ? "Активен" : "Отключен"}</StatusBadge>
                      {currentUserId === user.id ? <StatusBadge tone="neutral">Вы</StatusBadge> : null}
                    </div>
                    <p className="text-sm text-[var(--ink-soft)]">{user.email}</p>
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                      Права: {user.permissions.join(", ")}
                    </p>
                    <div className="flex flex-wrap gap-4 text-xs text-[var(--ink-soft)]">
                      <span>Создан: {formatDate(user.createdAt)}</span>
                      <span>Последняя активность: {formatDate(user.lastActiveAt)}</span>
                      {user.deactivatedAt ? <span>Отключен: {formatDate(user.deactivatedAt)}</span> : null}
                    </div>
                  </div>

                  <div className="flex flex-col gap-3 xl:min-w-[240px]">
                    <label className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                      Роль
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
                      {busy ? "Сохранение..." : user.enabled ? "Отключить пользователя" : "Включить пользователя"}
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </WidgetCard>

      <WidgetCard
        title="Журнал действий"
        subtitle="Последние события RBAC"
        loading={loading}
        error={error ?? undefined}
        empty={!loading && !error && auditEvents.length === 0}
        emptyMessage="События RBAC пока не записаны."
      >
        <div className="space-y-3">
          {auditEvents.slice(0, 12).map((event) => (
            <div key={event.id} className="rounded-[20px] border border-[var(--line)] bg-white/70 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone={event.outcome === "denied" ? "watch" : "neutral"}>{event.outcome}</StatusBadge>
                <p className="text-sm font-semibold">{event.event}</p>
              </div>
              <p className="mt-2 text-sm text-[var(--ink-soft)]">
                Инициатор: {event.actorId}
                {event.targetId ? ` -> Цель: ${event.targetId}` : ""}
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
