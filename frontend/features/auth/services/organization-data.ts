"use client";

import { apiEndpoints, requestJson } from "@/shared/api";
import { getDevAuthSession } from "@/features/auth/services/auth-data";
import type { OrganizationProfile } from "@/features/auth/types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function normalizeOrganization(payload: unknown): OrganizationProfile {
  const fallback = getDevAuthSession().organization;
  if (!isRecord(payload)) {
    return fallback;
  }

  const organization = isRecord(payload.organization) ? payload.organization : payload;
  return {
    id: typeof organization.id === "string" ? organization.id : fallback.id,
    name: typeof organization.name === "string" ? organization.name : fallback.name,
    plan: typeof organization.plan === "string" ? organization.plan : fallback.plan,
    status: typeof organization.status === "string" ? organization.status : fallback.status,
    createdAt: typeof organization.createdAt === "string" ? organization.createdAt : fallback.createdAt
  };
}

export async function fetchOrganizationProfile() {
  const payload = await requestJson<unknown>(apiEndpoints.organization);
  return normalizeOrganization(payload);
}
