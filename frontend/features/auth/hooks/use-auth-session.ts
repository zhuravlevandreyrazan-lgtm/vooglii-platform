"use client";

import { useEffect, useState } from "react";
import { formatApiErrorMessage } from "@/shared/api";
import { useDemoMode } from "@/shared/demo/demo-provider";
import { useWorkspaceContext } from "@/shared/workspace-context";
import {
  buildLocalAuthSession,
  buildAuthSessionSnapshot,
  fetchAuthSession,
  getDemoAuthSession
} from "@/features/auth/services/auth-data";
import type { AuthSessionSnapshot } from "@/features/auth/types";

export function useAuthSession() {
  const { enabled: demoEnabled, ready: demoReady } = useDemoMode();
  const workspace = useWorkspaceContext();
  const [snapshot, setSnapshot] = useState<AuthSessionSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);

    try {
      if (!workspace.ready) {
        return;
      }
      const session = demoEnabled
        ? buildLocalAuthSession({
            mode: "demo",
            organization: workspace.organization
              ? {
                  id: workspace.organization.id,
                  name: workspace.organization.name,
                  plan: workspace.organization.plan,
                  status: workspace.organization.status,
                  createdAt: workspace.organization.createdAt
                }
              : getDemoAuthSession().organization,
            cabinet: workspace.cabinet
              ? {
                  id: workspace.cabinet.id,
                  name: workspace.cabinet.name,
                  sellerId: workspace.cabinet.sellerId,
                  status: workspace.cabinet.status,
                  connected: workspace.cabinet.connected,
                  lastSyncAt: workspace.cabinet.lastSyncAt,
                  dataQuality: workspace.cabinet.dataQuality,
                  tokenStatus: workspace.cabinet.tokenStatus
                }
              : getDemoAuthSession().cabinet,
            user: getDemoAuthSession().user
          })
        : await fetchAuthSession();
      setSnapshot(buildAuthSessionSnapshot(session));
    } catch (loadError) {
      setError(formatApiErrorMessage(loadError));
      setSnapshot(buildAuthSessionSnapshot(getDemoAuthSession()));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!demoReady || !workspace.ready) {
      return;
    }
    void load();
  }, [demoEnabled, demoReady, workspace.ready, workspace.organization?.id, workspace.cabinet?.id]);

  return {
    session: snapshot?.session ?? null,
    user: snapshot?.user ?? null,
    organization: snapshot?.organization ?? null,
    cabinet: snapshot?.cabinet ?? null,
    loading,
    error,
    reload: load,
    authenticated: snapshot?.authenticated ?? false,
    diagnostics: snapshot?.diagnostics,
    context: snapshot?.context
  };
}
