"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchAutomationSnapshot,
  generateExportPreset,
  getAutomationMockSnapshot,
  updateScheduleState
} from "@/features/automation/services/automation-data";
import type { AutomationSnapshot, ExportFormat } from "@/features/automation/types";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { getDemoAutomationSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type UseAutomationDataResult = {
  data: AutomationSnapshot;
  loading: boolean;
  error: string | null;
  actionMessage: string | null;
  pendingAction: boolean;
  reload: () => void;
  lastUpdated: string | null;
  diagnostics: WorkspaceDiagnostics;
  generateExport: (payload: { workspace: string; format: ExportFormat; name?: string; sku?: string }) => Promise<void>;
  toggleSchedule: (scheduleId: string, enabled: boolean) => Promise<void>;
};

const INITIAL_DATA = getAutomationMockSnapshot();

export function useAutomationData(): UseAutomationDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const [data, setData] = useState<AutomationSnapshot>(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(INITIAL_DATA.lastUpdated ?? null);
  const [diagnostics, setDiagnostics] = useState<WorkspaceDiagnostics>(
    INITIAL_DATA.diagnostics ?? {
      source: "fallback",
      degraded: true,
      cached: false,
      stale: false,
      validationStatus: "fallback"
    }
  );
  const abortControllerRef = useRef<AbortController | null>(null);
  const reloadTickRef = useRef(0);
  const [reloadTick, setReloadTick] = useState(0);

  const reload = () => {
    reloadTickRef.current += 1;
    setReloadTick(reloadTickRef.current);
  };

  const load = async (controller: AbortController) => {
    setLoading(true);
    setError(null);

    try {
      const snapshot = demoModeEnabled ? getDemoAutomationSnapshot() : await fetchAutomationSnapshot(controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      setData(snapshot);
      setDiagnostics(snapshot.diagnostics ?? diagnostics);
      setLastUpdated(snapshot.lastUpdated ?? new Date().toISOString());
    } catch (loadError) {
      if (controller.signal.aborted) {
        return;
      }
      const fallbackSnapshot = getAutomationMockSnapshot();
      setError(`${FALLBACK_DATA_MESSAGE} ${formatApiErrorMessage(loadError)}`);
      setData(fallbackSnapshot);
      setDiagnostics(fallbackSnapshot.diagnostics ?? diagnostics);
      setLastUpdated(new Date().toISOString());
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const controller = new AbortController();
      abortControllerRef.current?.abort();
      abortControllerRef.current = controller;
      void load(controller);
    }, 500);

    return () => {
      window.clearTimeout(timer);
      abortControllerRef.current?.abort();
    };
  }, [demoModeEnabled, reloadTick]);

  const generateExport = async (payload: { workspace: string; format: ExportFormat; name?: string; sku?: string }) => {
    setPendingAction(true);
    setActionMessage(null);
    try {
      if (demoModeEnabled) {
        setActionMessage(`Demo export queued for ${payload.workspace} in ${payload.format}.`);
      } else {
        const generated = await generateExportPreset(payload);
        setActionMessage(`${generated.name} queued in ${generated.format} format.`);
      }
      reload();
    } catch (actionError) {
      setActionMessage(formatApiErrorMessage(actionError));
    } finally {
      setPendingAction(false);
    }
  };

  const toggleSchedule = async (scheduleId: string, enabled: boolean) => {
    setPendingAction(true);
    setActionMessage(null);
    try {
      if (demoModeEnabled) {
        setActionMessage(`Demo schedule ${enabled ? "enabled" : "paused"} for ${scheduleId}.`);
      } else {
        const updated = await updateScheduleState(scheduleId, { enabled });
        setActionMessage(`${updated.name} is now ${updated.enabled ? "enabled" : "paused"}.`);
      }
      reload();
    } catch (actionError) {
      setActionMessage(formatApiErrorMessage(actionError));
    } finally {
      setPendingAction(false);
    }
  };

  return {
    data,
    loading,
    error,
    actionMessage,
    pendingAction,
    reload,
    lastUpdated,
    diagnostics,
    generateExport,
    toggleSchedule
  };
}
