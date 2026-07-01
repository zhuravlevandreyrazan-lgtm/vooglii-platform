"use client";

import type { PlatformRole, UserProfile } from "@/features/auth/types";
import type { AuditEvent, UsersSnapshot } from "@/features/users/types";
import {
  ApiError,
  apiEndpoints,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeUser(value: unknown): UserProfile | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    typeof value.id !== "string" ||
    typeof value.name !== "string" ||
    typeof value.email !== "string" ||
    typeof value.role !== "string" ||
    typeof value.createdAt !== "string"
  ) {
    return null;
  }

  return {
    id: value.id,
    name: value.name,
    email: value.email,
    role: value.role as PlatformRole,
    permissions: Array.isArray(value.permissions)
      ? value.permissions.filter((item): item is UserProfile["permissions"][number] => typeof item === "string")
      : [],
    enabled: typeof value.enabled === "boolean" ? value.enabled : true,
    avatarUrl: typeof value.avatarUrl === "string" ? value.avatarUrl : null,
    createdAt: value.createdAt,
    lastActiveAt: typeof value.lastActiveAt === "string" ? value.lastActiveAt : null,
    deactivatedAt: typeof value.deactivatedAt === "string" ? value.deactivatedAt : null
  };
}

function normalizeAuditEvent(value: unknown): AuditEvent | null {
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    typeof value.event !== "string" ||
    typeof value.actorId !== "string" ||
    typeof value.outcome !== "string" ||
    typeof value.createdAt !== "string"
  ) {
    return null;
  }

  return {
    id: value.id,
    event: value.event,
    actorId: value.actorId,
    targetId: typeof value.targetId === "string" ? value.targetId : null,
    outcome: value.outcome,
    detail: typeof value.detail === "string" ? value.detail : null,
    metadata: isRecord(value.metadata) ? value.metadata : {},
    createdAt: value.createdAt
  };
}

export function buildUsersSnapshot(payload: {
  users: UserProfile[];
  availableRoles: PlatformRole[];
  auditEvents: AuditEvent[];
  diagnostics?: UsersSnapshot["diagnostics"];
}): UsersSnapshot {
  return {
    users: payload.users,
    availableRoles: payload.availableRoles,
    auditEvents: payload.auditEvents,
    diagnostics: payload.diagnostics ?? createFallbackDiagnostics()
  };
}

export async function fetchUsersSnapshot(signal?: AbortSignal) {
  const [usersPayload, auditPayload] = await Promise.all([
    requestJson<unknown>(apiEndpoints.users, { signal }),
    requestJson<unknown>(apiEndpoints.audit, { signal })
  ]);

  if (!isRecord(usersPayload) || !Array.isArray(usersPayload.users) || !Array.isArray(usersPayload.availableRoles)) {
    throw new ApiError("Users API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.users
    });
  }

  if (!isRecord(auditPayload) || !Array.isArray(auditPayload.events)) {
    throw new ApiError("Audit API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.audit
    });
  }

  const diagnostics = buildWorkspaceDiagnostics({
    runtime: normalizeRuntimeMetadata(usersPayload) ?? normalizeRuntimeMetadata(auditPayload),
    validationStatus: "ok"
  });

  return buildUsersSnapshot({
    users: usersPayload.users.map(normalizeUser).filter((item): item is UserProfile => Boolean(item)),
    availableRoles: usersPayload.availableRoles.filter((item): item is PlatformRole => typeof item === "string") as PlatformRole[],
    auditEvents: auditPayload.events.map(normalizeAuditEvent).filter((item): item is AuditEvent => Boolean(item)),
    diagnostics
  });
}

export async function updateUserRole(userId: string, role: PlatformRole) {
  const payload = await requestJson<unknown>(`${apiEndpoints.users}/${userId}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role })
  });

  if (!isRecord(payload) || !("user" in payload)) {
    throw new ApiError("User role update payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: `${apiEndpoints.users}/${userId}/role`
    });
  }

  const user = normalizeUser(payload.user);
  if (!user) {
    throw new ApiError("User role update payload has an invalid user shape.", {
      code: "invalid_shape",
      status: null,
      url: `${apiEndpoints.users}/${userId}/role`
    });
  }

  return user;
}

export async function updateUserStatus(userId: string, enabled: boolean) {
  const payload = await requestJson<unknown>(`${apiEndpoints.users}/${userId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled })
  });

  if (!isRecord(payload) || !("user" in payload)) {
    throw new ApiError("User status update payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: `${apiEndpoints.users}/${userId}/status`
    });
  }

  const user = normalizeUser(payload.user);
  if (!user) {
    throw new ApiError("User status update payload has an invalid user shape.", {
      code: "invalid_shape",
      status: null,
      url: `${apiEndpoints.users}/${userId}/status`
    });
  }

  return user;
}
