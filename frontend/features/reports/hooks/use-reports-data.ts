"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchReportsSnapshot,
  getReportsMockSnapshot
} from "@/features/reports/services/reports-data";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { getDemoReportsSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type { WorkspaceDiagnostics } from "@/shared/api";
import type { ReportsSnapshot } from "@/features/reports/types";

export type UseReportsDataResult = {
  data: ReportsSnapshot;
  loading: boolean;
  error: string | null;
  reload: () => void;
  lastUpdated: string | null;
  diagnostics: WorkspaceDiagnostics;
};

const INITIAL_DATA = getReportsMockSnapshot();

export function useReportsData(): UseReportsDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const [data, setData] = useState<ReportsSnapshot>(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  useEffect(() => {
    if (demoModeEnabled) {
      const demoSnapshot = getDemoReportsSnapshot();
      setLoading(false);
      setError(null);
      setData(demoSnapshot);
      setDiagnostics(demoSnapshot.diagnostics ?? diagnostics);
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
          const snapshot = await fetchReportsSnapshot(controller.signal);

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

          const fallbackSnapshot = getReportsMockSnapshot();
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
