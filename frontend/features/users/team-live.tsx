"use client";

import { useAuth } from "@/features/auth";
import { useUsersData } from "@/features/users/hooks/use-users-data";
import { TeamScreen } from "@/features/users/team-screen";

export function TeamLive() {
  const { user, can } = useAuth();
  const canViewUsers = can("users:view");
  const canManageUsers = can("users:manage");
  const { data, loading, error, pendingUserId, actionMessage, changeRole, toggleUser } = useUsersData(canViewUsers);

  return (
    <TeamScreen
      actionMessage={actionMessage}
      canManageUsers={canManageUsers}
      canViewUsers={canViewUsers}
      currentUserId={user?.id ?? null}
      data={data}
      error={error}
      loading={loading}
      onRoleChange={changeRole}
      onToggleUser={toggleUser}
      pendingUserId={pendingUserId}
    />
  );
}
