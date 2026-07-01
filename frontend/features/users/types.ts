import type { PlatformRole, UserProfile } from "@/features/auth/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type AuditEvent = {
  id: string;
  event: string;
  actorId: string;
  targetId?: string | null;
  outcome: string;
  detail?: string | null;
  metadata?: Record<string, unknown>;
  createdAt: string;
};

export type UsersSnapshot = {
  users: UserProfile[];
  availableRoles: PlatformRole[];
  auditEvents: AuditEvent[];
  diagnostics: WorkspaceDiagnostics;
};
