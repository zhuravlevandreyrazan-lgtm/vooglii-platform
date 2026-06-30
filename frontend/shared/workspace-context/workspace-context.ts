export type WorkspaceOrganization = {
  id: string;
  name: string;
  plan: string;
  status: string;
  createdAt: string;
  cabinetCount: number;
  health?: string | null;
};

export type WorkspaceCabinet = {
  id: string;
  organizationId: string;
  organizationName?: string | null;
  name: string;
  sellerId: string;
  status: string;
  connected: boolean;
  lastSyncAt?: string | null;
  dataQuality: string;
  tokenStatus: string;
  health?: string | null;
};

export type ActiveWorkspaceContext = {
  organizationId: string | null;
  cabinetId: string | null;
  mode: "live" | "demo" | "dev";
  lastChanged: string | null;
  organizationCount: number;
  cabinetCount: number;
};

export type WorkspaceContextValue = {
  organizations: WorkspaceOrganization[];
  cabinets: WorkspaceCabinet[];
  organization: WorkspaceOrganization | null;
  cabinet: WorkspaceCabinet | null;
  mode: "live" | "demo" | "dev";
  lastChanged: string | null;
  loading: boolean;
  ready: boolean;
  error: string | null;
  selectOrganization: (organizationId: string) => Promise<void>;
  selectCabinet: (cabinetId: string) => Promise<void>;
  reload: () => Promise<void>;
  context: ActiveWorkspaceContext;
};
