"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchAdvisorSnapshot,
  getAdvisorMockSnapshot
} from "@/features/advisor/services/advisor-data";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { getDemoAdvisorSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type { AdvisorSnapshot } from "@/features/advisor/types";
import type { WorkspaceDiagnostics } from "@/shared/api";

export type UseAdvisorDataResult = {
  data: AdvisorSnapshot;
  loading: boolean;
  error: string | null;
  reload: () => void;
  lastUpdated: string | null;
  diagnostics: WorkspaceDiagnostics;
};

const INITIAL_DATA = getAdvisorMockSnapshot();

export function useAdvisorData(): UseAdvisorDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const fallbackDiagnostics =
    INITIAL_DATA.diagnostics ?? {
      source: "fallback",
      degraded: true,
      cached: false,
      stale: false,
      validationStatus: "fallback" as const
    };
  const [data, setData] = useState<AdvisorSnapshot>(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(INITIAL_DATA.lastUpdated ?? null);
  const [diagnostics, setDiagnostics] = useState<WorkspaceDiagnostics>(fallbackDiagnostics);
  const abortControllerRef = useRef<AbortController | null>(null);
  const reloadTickRef = useRef(0);
  const [reloadTick, setReloadTick] = useState(0);

  const reload = () => {
    reloadTickRef.current += 1;
    setReloadTick(reloadTickRef.current);
  };

  useEffect(() => {
    if (demoModeEnabled) {
      const demoSnapshot = getDemoAdvisorSnapshot();
      setLoading(false);
      setError(null);
      setData(demoSnapshot);
      setDiagnostics(demoSnapshot.diagnostics ?? fallbackDiagnostics);
      setLastUpdated(demoSnapshot.lastUpdated ?? new Date().toISOString());
      return () => {
        abortControllerRef.current?.abort();
      };
    }

    const timer = window.setTimeout(() => {
      const controller = new AbortController();
      abortControllerRef.current?.abort();
      abortControllerRef.current = controller;

      const run = async () => {
        setLoading(true);
        setError(null);

        try {
          const snapshot = await fetchAdvisorSnapshot(controller.signal);

          if (controller.signal.aborted) {
            return;
          }

          setData(snapshot);
          setDiagnostics(snapshot.diagnostics ?? fallbackDiagnostics);
          setLastUpdated(snapshot.lastUpdated ?? new Date().toISOString());
        } catch (loadError) {
          if (controller.signal.aborted) {
            return;
          }

          const fallbackSnapshot = getAdvisorMockSnapshot();
          setError(`${FALLBACK_DATA_MESSAGE} ${formatApiErrorMessage(loadError)}`);
          setData(fallbackSnapshot);
          setDiagnostics(fallbackSnapshot.diagnostics ?? fallbackDiagnostics);
          setLastUpdated(new Date().toISOString());
        } finally {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        }
      };

      void run();
    }, 650);

    return () => {
      window.clearTimeout(timer);
      abortControllerRef.current?.abort();
    };
  }, [demoModeEnabled, reloadTick]);

  return {
    data,
    loading,
    error,
    reload,
    lastUpdated,
    diagnostics
  };
}
