"use client";

import { apiEndpoints, requestJson } from "@/shared/api";
import { getDevAuthSession } from "@/features/auth/services/auth-data";
import type { WbCabinetProfile } from "@/features/auth/types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function normalizeCabinet(payload: unknown): WbCabinetProfile {
  const fallback = getDevAuthSession().cabinet;
  if (!isRecord(payload)) {
    return fallback;
  }

  const cabinet = isRecord(payload.cabinet) ? payload.cabinet : payload;
  return {
    id: typeof cabinet.id === "string" ? cabinet.id : fallback.id,
    name: typeof cabinet.name === "string" ? cabinet.name : fallback.name,
    sellerId: typeof cabinet.sellerId === "string" ? cabinet.sellerId : fallback.sellerId,
    status: typeof cabinet.status === "string" ? cabinet.status : fallback.status,
    connected: typeof cabinet.connected === "boolean" ? cabinet.connected : fallback.connected,
    lastSyncAt: typeof cabinet.lastSyncAt === "string" ? cabinet.lastSyncAt : fallback.lastSyncAt,
    dataQuality: typeof cabinet.dataQuality === "string" ? cabinet.dataQuality : fallback.dataQuality,
    tokenStatus: typeof cabinet.tokenStatus === "string" ? cabinet.tokenStatus : fallback.tokenStatus
  };
}

export async function fetchWbCabinetProfile() {
  const payload = await requestJson<unknown>(apiEndpoints.wbCabinet);
  return normalizeCabinet(payload);
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
