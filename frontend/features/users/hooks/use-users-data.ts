"use client";

import { useEffect, useState } from "react";
import type { PlatformRole } from "@/features/auth/types";
import type { UsersSnapshot } from "@/features/users/types";
import { fetchUsersSnapshot, updateUserRole, updateUserStatus } from "@/features/users/services/users-data";
import { formatApiErrorMessage } from "@/shared/api";

export function useUsersData(enabled: boolean) {
  const [data, setData] = useState<UsersSnapshot | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const [pendingUserId, setPendingUserId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const load = async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setData(await fetchUsersSnapshot());
    } catch (loadError) {
      setError(formatApiErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [enabled]);

  const changeRole = async (userId: string, role: PlatformRole) => {
    setPendingUserId(userId);
    setActionMessage(null);
    try {
      await updateUserRole(userId, role);
      await load();
      setActionMessage("Role updated.");
    } catch (actionError) {
      setActionMessage(formatApiErrorMessage(actionError));
    } finally {
      setPendingUserId(null);
    }
  };

  const toggleUser = async (userId: string, enabledValue: boolean) => {
    setPendingUserId(userId);
    setActionMessage(null);
    try {
      await updateUserStatus(userId, enabledValue);
      await load();
      setActionMessage(enabledValue ? "User enabled." : "User disabled.");
    } catch (actionError) {
      setActionMessage(formatApiErrorMessage(actionError));
    } finally {
      setPendingUserId(null);
    }
  };

  return {
    data,
    loading,
    error,
    pendingUserId,
    actionMessage,
    reload: load,
    changeRole,
    toggleUser
  };
}
