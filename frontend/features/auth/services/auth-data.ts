"use client";

import { apiEndpoints, requestJson } from "@/shared/api";
import type { AuthSession, AuthSessionSnapshot, OrganizationProfile, UserProfile, WbCabinetProfile } from "@/features/auth/types";

const DEV_USER: UserProfile = {
  id: "user_dev_founder",
  name: "Andrey Voronov",
  email: "andrey@vooglii.local",
  role: "owner",
  avatarUrl: null,
  createdAt: "2026-06-01T09:00:00Z"
};

const DEV_ORGANIZATION: OrganizationProfile = {
  id: "org_vooglii_beta",
  name: "VOOGLII Beta Lab",
  plan: "beta",
  status: "active",
  createdAt: "2026-06-03T12:00:00Z"
};

const DEV_CABINET: WbCabinetProfile = {
  id: "cabinet_dev_primary",
  name: "Wildberries Main Cabinet",
  sellerId: "WB-458210",
  status: "connected",
  connected: true,
  lastSyncAt: "2026-06-30T09:45:00Z",
  dataQuality: "high",
  tokenStatus: "safe_placeholder"
};

export function getDevAuthSession(): AuthSession {
  return {
    authenticated: true,
    user: DEV_USER,
    organization: DEV_ORGANIZATION,
    cabinet: DEV_CABINET,
    runtime: {
      source: "dev",
      cached: false,
      stale: false,
      degraded: false
    }
  };
}

export function getDemoAuthSession(): AuthSession {
  return {
    authenticated: true,
    user: {
      ...DEV_USER,
      id: "user_demo_operator",
      name: "Daria Kuznetsova",
      email: "demo@vooglii.local",
      role: "demo_admin"
    },
    organization: {
      ...DEV_ORGANIZATION,
      id: "org_demo_showcase",
      name: "Northwind Market Studio",
      plan: "demo",
      status: "showcase"
    },
    cabinet: {
      ...DEV_CABINET,
      id: "cabinet_demo_showcase",
      name: "WB Showcase Cabinet",
      sellerId: "WB-993104",
      status: "demo_connected",
      dataQuality: "showcase"
    },
    runtime: {
      source: "demo",
      cached: false,
      stale: false,
      degraded: false
    }
  };
}

export function buildLocalAuthSession(payload: {
  mode: "demo" | "dev";
  organization: OrganizationProfile;
  cabinet: WbCabinetProfile;
  user?: UserProfile;
}): AuthSession {
  return {
    authenticated: true,
    user: payload.user ?? (payload.mode === "demo" ? getDemoAuthSession().user : DEV_USER),
    organization: payload.organization,
    cabinet: payload.cabinet,
    runtime: {
      source: payload.mode,
      cached: false,
      stale: false,
      degraded: false
    }
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeUserProfile(value: unknown, fallback: UserProfile): UserProfile {
  if (!isRecord(value)) {
    return fallback;
  }

  return {
    id: typeof value.id === "string" ? value.id : fallback.id,
    name: typeof value.name === "string" ? value.name : fallback.name,
    email: typeof value.email === "string" ? value.email : fallback.email,
    role: typeof value.role === "string" ? value.role : fallback.role,
    avatarUrl: typeof value.avatarUrl === "string" ? value.avatarUrl : fallback.avatarUrl,
    createdAt: typeof value.createdAt === "string" ? value.createdAt : fallback.createdAt
  };
}

function normalizeOrganizationProfile(value: unknown, fallback: OrganizationProfile): OrganizationProfile {
  if (!isRecord(value)) {
    return fallback;
  }

  return {
    id: typeof value.id === "string" ? value.id : fallback.id,
    name: typeof value.name === "string" ? value.name : fallback.name,
    plan: typeof value.plan === "string" ? value.plan : fallback.plan,
    status: typeof value.status === "string" ? value.status : fallback.status,
    createdAt: typeof value.createdAt === "string" ? value.createdAt : fallback.createdAt
  };
}

function normalizeCabinetProfile(value: unknown, fallback: WbCabinetProfile): WbCabinetProfile {
  if (!isRecord(value)) {
    return fallback;
  }

  return {
    id: typeof value.id === "string" ? value.id : fallback.id,
    name: typeof value.name === "string" ? value.name : fallback.name,
    sellerId: typeof value.sellerId === "string" ? value.sellerId : fallback.sellerId,
    status: typeof value.status === "string" ? value.status : fallback.status,
    connected: typeof value.connected === "boolean" ? value.connected : fallback.connected,
    lastSyncAt: typeof value.lastSyncAt === "string" ? value.lastSyncAt : fallback.lastSyncAt,
    dataQuality: typeof value.dataQuality === "string" ? value.dataQuality : fallback.dataQuality,
    tokenStatus: typeof value.tokenStatus === "string" ? value.tokenStatus : fallback.tokenStatus
  };
}

export function normalizeAuthSession(payload: unknown, fallback: AuthSession): AuthSession {
  if (!isRecord(payload)) {
    return fallback;
  }

  return {
    authenticated: typeof payload.authenticated === "boolean" ? payload.authenticated : fallback.authenticated,
    user: normalizeUserProfile(payload.user, fallback.user),
    organization: normalizeOrganizationProfile(payload.organization, fallback.organization),
    cabinet: normalizeCabinetProfile(payload.cabinet, fallback.cabinet),
    runtime: isRecord(payload.runtime)
      ? {
          source: typeof payload.runtime.source === "string" ? payload.runtime.source : fallback.runtime?.source,
          cached: typeof payload.runtime.cached === "boolean" ? payload.runtime.cached : false,
          stale: typeof payload.runtime.stale === "boolean" ? payload.runtime.stale : false,
          degraded: typeof payload.runtime.degraded === "boolean" ? payload.runtime.degraded : false,
          duration_ms: typeof payload.runtime.duration_ms === "number" ? payload.runtime.duration_ms : undefined
        }
      : fallback.runtime
  };
}

export async function fetchAuthSession(): Promise<AuthSession> {
  const payload = await requestJson<unknown>(apiEndpoints.authSession);
  return normalizeAuthSession(payload, getDevAuthSession());
}

export function buildAuthSessionSnapshot(session: AuthSession): AuthSessionSnapshot {
  const runtimeSource = session.runtime?.source === "demo" ? "demo" : session.runtime?.source === "live" ? "live" : "dev";
  return {
    session,
    user: session.user,
    organization: session.organization,
    cabinet: session.cabinet,
    authenticated: session.authenticated,
    diagnostics: {
      source: runtimeSource,
      degraded: Boolean(session.runtime?.degraded),
      cached: Boolean(session.runtime?.cached),
      stale: Boolean(session.runtime?.stale),
      durationMs: session.runtime?.duration_ms,
      validationStatus: "ok"
    },
    context: {
      organizationId: session.organization.id,
      cabinetId: session.cabinet.id,
      mode: runtimeSource
    }
  };
}
