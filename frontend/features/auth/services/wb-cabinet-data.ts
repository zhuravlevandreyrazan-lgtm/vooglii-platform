"use client";

import { apiEndpoints, requestJson } from "@/shared/api";
import { getDevAuthSession } from "@/features/auth/services/auth-data";
import type { WbCabinetProfile } from "@/features/auth/types";

type WbCabinetFormPayload = {
  organizationId?: string | null;
  name: string;
  sellerId?: string | null;
  scopes?: string[];
  connected?: boolean;
  tokens?: Record<string, string | null>;
};

export type WbSyncPayload = {
  type: string;
  dateFrom?: string | null;
  dateTo?: string | null;
};

export type WbApiHealthItem = {
  section: string;
  status: string;
  lastSuccessAt?: string | null;
  lastErrorAt?: string | null;
  lastErrorMessage?: string | null;
  message?: string | null;
  requiredAction?: string | null;
};

export type WbSyncJob = {
  id: string;
  cabinetId: string;
  type: string;
  status: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs?: number | null;
  recordsLoaded: number;
  errorMessage?: string | null;
  runtimeSource?: string | null;
  meta?: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function normalizeCabinet(payload: unknown): WbCabinetProfile {
  const fallback = getDevAuthSession().cabinet;
  if (!isRecord(payload)) {
    return fallback;
  }

  const cabinet = isRecord(payload.cabinet) ? payload.cabinet : payload;
  const rawTokens = isRecord(cabinet.tokens) ? cabinet.tokens : {};

  return {
    id: typeof cabinet.id === "string" ? cabinet.id : fallback.id,
    organizationId: typeof cabinet.organizationId === "string" ? cabinet.organizationId : fallback.organizationId,
    organizationName: typeof cabinet.organizationName === "string" ? cabinet.organizationName : fallback.organizationName,
    name: typeof cabinet.name === "string" ? cabinet.name : fallback.name,
    sellerId: typeof cabinet.sellerId === "string" ? cabinet.sellerId : fallback.sellerId,
    status: typeof cabinet.status === "string" ? cabinet.status : fallback.status,
    connected: typeof cabinet.connected === "boolean" ? cabinet.connected : fallback.connected,
    lastSyncAt: typeof cabinet.lastSyncAt === "string" ? cabinet.lastSyncAt : fallback.lastSyncAt,
    dataQuality: typeof cabinet.dataQuality === "string" ? cabinet.dataQuality : fallback.dataQuality,
    tokenStatus: typeof cabinet.tokenStatus === "string" ? cabinet.tokenStatus : fallback.tokenStatus,
    health: typeof cabinet.health === "string" ? cabinet.health : fallback.health,
    lastSyncStatus: typeof cabinet.lastSyncStatus === "string" ? cabinet.lastSyncStatus : fallback.lastSyncStatus,
    syncMessage: typeof cabinet.syncMessage === "string" ? cabinet.syncMessage : fallback.syncMessage,
    lastCheckedAt: typeof cabinet.lastCheckedAt === "string" ? cabinet.lastCheckedAt : fallback.lastCheckedAt,
    createdAt: typeof cabinet.createdAt === "string" ? cabinet.createdAt : fallback.createdAt,
    updatedAt: typeof cabinet.updatedAt === "string" ? cabinet.updatedAt : fallback.updatedAt,
    scopes: Array.isArray(cabinet.scopes) ? cabinet.scopes.filter((item): item is string => typeof item === "string") : fallback.scopes,
    tokens: {
      seller: typeof rawTokens.seller === "string" ? rawTokens.seller : null,
      statistics: typeof rawTokens.statistics === "string" ? rawTokens.statistics : null,
      advertising: typeof rawTokens.advertising === "string" ? rawTokens.advertising : null,
      finance: typeof rawTokens.finance === "string" ? rawTokens.finance : null
    }
  };
}

function normalizeCabinetList(payload: unknown): WbCabinetProfile[] {
  if (!isRecord(payload) || !Array.isArray(payload.cabinets)) {
    return [];
  }
  return payload.cabinets.map((item) => normalizeCabinet(item));
}

function cabinetUrl(cabinetId?: string) {
  return cabinetId ? `${apiEndpoints.wbCabinetsManage}/${cabinetId}` : apiEndpoints.wbCabinetsManage;
}

export async function fetchWbCabinetProfile() {
  const payload = await requestJson<unknown>(apiEndpoints.wbCabinet);
  return normalizeCabinet(payload);
}

export async function fetchWbCabinets() {
  const payload = await requestJson<unknown>(apiEndpoints.wbCabinetsManage);
  return normalizeCabinetList(payload);
}

export async function selectWbCabinet(cabinetId: string) {
  await requestJson(apiEndpoints.wbCabinetsSelect, {
    method: "POST",
    body: JSON.stringify({ cabinetId })
  });
}

export async function createWbCabinet(input: WbCabinetFormPayload) {
  const payload = await requestJson<unknown>(apiEndpoints.wbCabinetsManage, {
    method: "POST",
    body: JSON.stringify(input)
  });
  return normalizeCabinet(payload);
}

export async function updateWbCabinet(cabinetId: string, input: Partial<WbCabinetFormPayload>) {
  const payload = await requestJson<unknown>(cabinetUrl(cabinetId), {
    method: "PATCH",
    body: JSON.stringify(input)
  });
  return normalizeCabinet(payload);
}

export async function deleteWbCabinet(cabinetId: string) {
  const payload = await requestJson<unknown>(cabinetUrl(cabinetId), {
    method: "DELETE"
  });
  return normalizeCabinet(payload);
}

export async function testWbCabinet(cabinetId: string) {
  return requestJson<{
    cabinet: WbCabinetProfile;
    status: string;
    checks: Array<{ section: string; status: string; message: string; details?: Record<string, unknown> }>;
  }>(`${cabinetUrl(cabinetId)}/test`, {
    method: "POST"
  });
}

export async function syncWbCabinet(cabinetId: string, input: WbSyncPayload) {
  return requestJson<{
    cabinet: WbCabinetProfile;
    job?: WbSyncJob | null;
    results: Record<string, unknown>;
  }>(`${cabinetUrl(cabinetId)}/sync`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function fetchWbCabinetSyncStatus(cabinetId: string) {
  return requestJson<{
    cabinetId: string;
    latestJob?: WbSyncJob | null;
    history: WbSyncJob[];
  }>(`${cabinetUrl(cabinetId)}/sync-status`);
}

export async function fetchWbCabinetApiHealth(cabinetId: string) {
  const payload = await requestJson<{ cabinetId: string; health: WbApiHealthItem[] }>(`${cabinetUrl(cabinetId)}/api-health`);
  return Array.isArray(payload.health) ? payload.health : [];
}

export async function connectWbCabinet() {
  const payload = await requestJson<unknown>(apiEndpoints.wbCabinetConnect, {
    method: "POST"
  });
  return normalizeCabinet(payload);
}

export async function disconnectWbCabinet() {
  const payload = await requestJson<unknown>(apiEndpoints.wbCabinetDisconnect, {
    method: "POST"
  });
  return normalizeCabinet(payload);
}
