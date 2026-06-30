"use client";

import { createContext, useEffect, useMemo, useState } from "react";
import { apiEndpoints, formatApiErrorMessage, requestJson } from "@/shared/api";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type {
  ActiveWorkspaceContext,
  WorkspaceCabinet,
  WorkspaceContextValue,
  WorkspaceOrganization
} from "@/shared/workspace-context/workspace-context";

type RawWorkspaceContextResponse = {
  organizationId?: string | null;
  cabinetId?: string | null;
  mode?: string;
  lastChanged?: string | null;
  organizationCount?: number;
  cabinetCount?: number;
};

type RawOrganizationsResponse = {
  organizations?: WorkspaceOrganization[];
  activeOrganizationId?: string | null;
};

type RawCabinetsResponse = {
  cabinets?: WorkspaceCabinet[];
  activeCabinetId?: string | null;
  organizationId?: string | null;
};

const DEMO_ORGANIZATIONS: WorkspaceOrganization[] = [
  {
    id: "org_vooglii_demo",
    name: "VOOGLII Demo",
    plan: "enterprise_demo",
    status: "active",
    createdAt: "2026-06-01T09:00:00Z",
    cabinetCount: 2,
    health: "Healthy"
  },
  {
    id: "org_test_seller",
    name: "Test Seller",
    plan: "growth",
    status: "active",
    createdAt: "2026-06-10T12:00:00Z",
    cabinetCount: 2,
    health: "Watch"
  },
  {
    id: "org_agency_demo",
    name: "Agency Demo",
    plan: "agency",
    status: "active",
    createdAt: "2026-06-15T15:00:00Z",
    cabinetCount: 2,
    health: "Healthy"
  }
];

const DEMO_CABINETS: WorkspaceCabinet[] = [
  {
    id: "cabinet_vooglii_main",
    organizationId: "org_vooglii_demo",
    organizationName: "VOOGLII Demo",
    name: "VOOGLII Main Cabinet",
    sellerId: "WB-458210",
    status: "demo_connected",
    connected: true,
    lastSyncAt: "2026-06-30T09:45:00Z",
    dataQuality: "showcase",
    tokenStatus: "safe_placeholder",
    health: "Healthy"
  },
  {
    id: "cabinet_vooglii_home",
    organizationId: "org_vooglii_demo",
    organizationName: "VOOGLII Demo",
    name: "VOOGLII Home & Living",
    sellerId: "WB-458211",
    status: "demo_connected",
    connected: true,
    lastSyncAt: "2026-06-30T09:42:00Z",
    dataQuality: "showcase",
    tokenStatus: "safe_placeholder",
    health: "Healthy"
  },
  {
    id: "cabinet_test_fashion",
    organizationId: "org_test_seller",
    organizationName: "Test Seller",
    name: "Test Seller Fashion",
    sellerId: "WB-553901",
    status: "demo_connected",
    connected: true,
    lastSyncAt: "2026-06-30T08:55:00Z",
    dataQuality: "demo_medium",
    tokenStatus: "safe_placeholder",
    health: "Watch"
  },
  {
    id: "cabinet_test_beauty",
    organizationId: "org_test_seller",
    organizationName: "Test Seller",
    name: "Test Seller Beauty",
    sellerId: "WB-553902",
    status: "demo_review",
    connected: true,
    lastSyncAt: "2026-06-30T08:40:00Z",
    dataQuality: "demo_pending",
    tokenStatus: "safe_placeholder",
    health: "Watch"
  },
  {
    id: "cabinet_agency_brand_a",
    organizationId: "org_agency_demo",
    organizationName: "Agency Demo",
    name: "Agency Brand A",
    sellerId: "WB-771100",
    status: "demo_connected",
    connected: true,
    lastSyncAt: "2026-06-30T11:10:00Z",
    dataQuality: "showcase",
    tokenStatus: "safe_placeholder",
    health: "Healthy"
  },
  {
    id: "cabinet_agency_brand_b",
    organizationId: "org_agency_demo",
    organizationName: "Agency Demo",
    name: "Agency Brand B",
    sellerId: "WB-771101",
    status: "demo_connected",
    connected: true,
    lastSyncAt: "2026-06-30T10:58:00Z",
    dataQuality: "showcase",
    tokenStatus: "safe_placeholder",
    health: "Healthy"
  }
];

export const WorkspaceContextReact = createContext<WorkspaceContextValue | null>(null);

function firstCabinetForOrganization(organizationId: string) {
  return DEMO_CABINETS.find((item) => item.organizationId === organizationId) ?? null;
}

function buildDemoState(organizationId?: string | null, cabinetId?: string | null): WorkspaceContextValue {
  const organization =
    DEMO_ORGANIZATIONS.find((item) => item.id === organizationId) ??
    DEMO_ORGANIZATIONS[0] ??
    null;
  const cabinets = DEMO_CABINETS.filter((item) => item.organizationId === organization?.id);
  const cabinet =
    cabinets.find((item) => item.id === cabinetId) ??
    (organization ? firstCabinetForOrganization(organization.id) : null);

  return {
    organizations: DEMO_ORGANIZATIONS,
    cabinets,
    organization,
    cabinet,
    mode: "demo",
    lastChanged: new Date().toISOString(),
    loading: false,
    ready: true,
    error: null,
    selectOrganization: async () => undefined,
    selectCabinet: async () => undefined,
    reload: async () => undefined,
    context: {
      organizationId: organization?.id ?? null,
      cabinetId: cabinet?.id ?? null,
      mode: "demo",
      lastChanged: new Date().toISOString(),
      organizationCount: DEMO_ORGANIZATIONS.length,
      cabinetCount: DEMO_CABINETS.length
    }
  };
}

export function WorkspaceContextProvider({ children }: { children: React.ReactNode }) {
  const { enabled: demoEnabled, ready: demoReady } = useDemoMode();
  const [organizations, setOrganizations] = useState<WorkspaceOrganization[]>([]);
  const [cabinets, setCabinets] = useState<WorkspaceCabinet[]>([]);
  const [organization, setOrganization] = useState<WorkspaceOrganization | null>(null);
  const [cabinet, setCabinet] = useState<WorkspaceCabinet | null>(null);
  const [context, setContext] = useState<ActiveWorkspaceContext>({
    organizationId: null,
    cabinetId: null,
    mode: "dev",
    lastChanged: null,
    organizationCount: 0,
    cabinetCount: 0
  });
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyDemoSelection = (organizationId?: string | null, cabinetId?: string | null) => {
    const demoState = buildDemoState(organizationId, cabinetId);
    setOrganizations(demoState.organizations);
    setCabinets(demoState.cabinets);
    setOrganization(demoState.organization);
    setCabinet(demoState.cabinet);
    setContext(demoState.context);
    setError(null);
    setLoading(false);
    setReady(true);
  };

  const loadLiveState = async () => {
    setLoading(true);
    setError(null);
    try {
      const [contextPayload, organizationsPayload] = await Promise.all([
        requestJson<RawWorkspaceContextResponse>(apiEndpoints.workspaceContext),
        requestJson<RawOrganizationsResponse>(apiEndpoints.organizations)
      ]);

      const organizationId = contextPayload.organizationId ?? organizationsPayload.activeOrganizationId ?? null;
      const organizationsList = Array.isArray(organizationsPayload.organizations) ? organizationsPayload.organizations : [];
      const cabinetsPayload = await requestJson<RawCabinetsResponse>(apiEndpoints.wbCabinets);
      const cabinetsList = Array.isArray(cabinetsPayload.cabinets) ? cabinetsPayload.cabinets : [];
      const activeOrganization =
        organizationsList.find((item) => item.id === organizationId) ??
        organizationsList[0] ??
        null;
      const activeCabinet =
        cabinetsList.find((item) => item.id === (contextPayload.cabinetId ?? cabinetsPayload.activeCabinetId ?? null)) ??
        cabinetsList[0] ??
        null;

      setOrganizations(organizationsList);
      setCabinets(cabinetsList);
      setOrganization(activeOrganization);
      setCabinet(activeCabinet);
      setContext({
        organizationId: activeOrganization?.id ?? null,
        cabinetId: activeCabinet?.id ?? null,
        mode: contextPayload.mode === "live" ? "live" : "dev",
        lastChanged: contextPayload.lastChanged ?? null,
        organizationCount: typeof contextPayload.organizationCount === "number" ? contextPayload.organizationCount : organizationsList.length,
        cabinetCount: typeof contextPayload.cabinetCount === "number" ? contextPayload.cabinetCount : cabinetsList.length
      });
    } catch (loadError) {
      setError(formatApiErrorMessage(loadError));
    } finally {
      setLoading(false);
      setReady(true);
    }
  };

  useEffect(() => {
    if (!demoReady) {
      return;
    }
    if (demoEnabled) {
      applyDemoSelection(context.organizationId, context.cabinetId);
      return;
    }
    void loadLiveState();
  }, [demoEnabled, demoReady]);

  const selectOrganization = async (organizationId: string) => {
    if (demoEnabled) {
      applyDemoSelection(organizationId, null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await requestJson(apiEndpoints.organizationsSelect, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ organizationId })
      });
      await loadLiveState();
    } catch (actionError) {
      setError(formatApiErrorMessage(actionError));
      setLoading(false);
    }
  };

  const selectCabinet = async (cabinetId: string) => {
    if (demoEnabled) {
      const nextCabinet = DEMO_CABINETS.find((item) => item.id === cabinetId) ?? null;
      applyDemoSelection(nextCabinet?.organizationId ?? context.organizationId, cabinetId);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await requestJson(apiEndpoints.wbCabinetsSelect, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cabinetId })
      });
      await loadLiveState();
    } catch (actionError) {
      setError(formatApiErrorMessage(actionError));
      setLoading(false);
    }
  };

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      organizations,
      cabinets,
      organization,
      cabinet,
      mode: demoEnabled ? "demo" : context.mode,
      lastChanged: context.lastChanged,
      loading,
      ready,
      error,
      selectOrganization,
      selectCabinet,
      reload: demoEnabled ? async () => applyDemoSelection(context.organizationId, context.cabinetId) : loadLiveState,
      context
    }),
    [organizations, cabinets, organization, cabinet, demoEnabled, context, loading, ready, error]
  );

  return <WorkspaceContextReact.Provider value={value}>{children}</WorkspaceContextReact.Provider>;
}
