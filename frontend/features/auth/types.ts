import type { WorkspaceContext, WorkspaceDiagnostics } from "@/shared/api";

export type PlatformRole = "owner" | "admin" | "manager" | "analyst" | "viewer";
export type PlatformPermission =
  | "dashboard:view"
  | "reports:view"
  | "analytics:view"
  | "ads:view"
  | "finance:view"
  | "users:view"
  | "users:manage"
  | "settings:manage";

export type AuthRuntime = {
  duration_ms?: number;
  cached?: boolean;
  stale?: boolean;
  degraded?: boolean;
  source?: string;
};

export type UserProfile = {
  id: string;
  name: string;
  email: string;
  role: PlatformRole;
  permissions: PlatformPermission[];
  enabled: boolean;
  avatarUrl?: string | null;
  createdAt: string;
  lastActiveAt?: string | null;
  deactivatedAt?: string | null;
};

export type OrganizationProfile = {
  id: string;
  name: string;
  plan: string;
  status: string;
  createdAt: string;
};

export type WbCabinetProfile = {
  id: string;
  name: string;
  sellerId: string;
  status: string;
  connected: boolean;
  lastSyncAt?: string | null;
  dataQuality: string;
  tokenStatus: string;
};

export type AuthSession = {
  authenticated: boolean;
  user: UserProfile;
  organization: OrganizationProfile;
  cabinet: WbCabinetProfile;
  runtime?: AuthRuntime;
};

export type AuthSessionSnapshot = {
  session: AuthSession;
  user: UserProfile;
  organization: OrganizationProfile;
  cabinet: WbCabinetProfile;
  authenticated: boolean;
  diagnostics: WorkspaceDiagnostics;
  context: WorkspaceContext;
};
