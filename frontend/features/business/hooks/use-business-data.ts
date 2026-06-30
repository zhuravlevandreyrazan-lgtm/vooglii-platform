"use client";

import { useEffect, useRef, useState } from "react";
import { buildBusinessAlerts } from "@/features/business/business-alerts";
import { buildBusinessInsights } from "@/features/business/business-insights";
import { buildBusinessKpis } from "@/features/business/business-kpis";
import {
  fetchBusinessSnapshot,
  getBusinessMockSnapshot
} from "@/features/business/services/business-data";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { useDemoMode } from "@/shared/demo/demo-provider";
import { getDemoBusinessSnapshot } from "@/shared/demo/demo-data";
import type { WorkspaceDiagnostics } from "@/shared/api";
import type { BusinessAlert, BusinessInsight, BusinessKpis, BusinessSnapshot } from "@/features/business/types";

export type UseBusinessDataResult = {
  data: BusinessSnapshot;
  kpis: BusinessKpis;
  insight: BusinessInsight;
  alerts: BusinessAlert[];
  loading: boolean;
  error: string | null;
  reload: () => void;
  lastUpdated: string | null;
  diagnostics: WorkspaceDiagnostics;
};

const INITIAL_DATA = getBusinessMockSnapshot();

export function useBusinessData(): UseBusinessDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const [data, setData] = useState<BusinessSnapshot>(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(INITIAL_DATA.generatedAt ?? null);
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

  const kpis = buildBusinessKpis(data);
  const insight = buildBusinessInsights(kpis);
  const alerts = buildBusinessAlerts(kpis, insight);

  useEffect(() => {
    if (demoModeEnabled) {
      const demoSnapshot = getDemoBusinessSnapshot();
      setLoading(false);
      setError(null);
      setData(demoSnapshot);
      setDiagnostics(demoSnapshot.diagnostics ?? diagnostics);
      setLastUpdated(demoSnapshot.generatedAt ?? new Date().toISOString());
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
          const snapshot = await fetchBusinessSnapshot(controller.signal);

          if (controller.signal.aborted) {
            return;
          }

          setData(snapshot);
          setDiagnostics(snapshot.diagnostics ?? diagnostics);
          setLastUpdated(snapshot.generatedAt ?? new Date().toISOString());
        } catch (loadError) {
          if (controller.signal.aborted) {
            return;
          }

          setError(formatApiErrorMessage(loadError));
          const fallbackSnapshot = getBusinessMockSnapshot();
          setData(fallbackSnapshot);
          setDiagnostics(fallbackSnapshot.diagnostics ?? diagnostics);
          setError(`${FALLBACK_DATA_MESSAGE} ${formatApiErrorMessage(loadError)}`);
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
    kpis,
    insight,
    alerts,
    loading,
    error,
    reload,
    lastUpdated,
    diagnostics
  };
}
