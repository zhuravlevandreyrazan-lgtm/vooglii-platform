"use client";

import { useEffect, useRef, useState } from "react";
import type { WorkspaceDiagnostics } from "@/shared/api";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type { ForecastSimulation, ForecastSnapshot } from "@/features/forecast/types";
import {
  fetchForecastSnapshot,
  getForecastMockSnapshot,
  simulateForecast
} from "@/services/forecast-api";

export type UseForecastDataResult = {
  data: ForecastSnapshot;
  loading: boolean;
  error: string | null;
  reload: () => void;
  lastUpdated: string | null;
  diagnostics: WorkspaceDiagnostics;
  simulation: ForecastSimulation | null;
  simulationLoading: boolean;
  simulateAction: (type: "increase_ads" | "reduce_ads" | "restock") => Promise<void>;
};

const INITIAL_DATA = getForecastMockSnapshot();

export function useForecastData(): UseForecastDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const [data, setData] = useState<ForecastSnapshot>(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(INITIAL_DATA.generatedAt);
  const [diagnostics, setDiagnostics] = useState<WorkspaceDiagnostics>(
    INITIAL_DATA.diagnostics ?? {
      source: "fallback",
      degraded: true,
      cached: false,
      stale: false,
      validationStatus: "fallback"
    }
  );
  const [simulation, setSimulation] = useState<ForecastSimulation | null>(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const reload = () => {
    setReloadTick((value) => value + 1);
  };

  useEffect(() => {
    if (demoModeEnabled) {
      setData(INITIAL_DATA);
      setDiagnostics(INITIAL_DATA.diagnostics ?? diagnostics);
      setLastUpdated(new Date().toISOString());
      setError(null);
      setLoading(false);
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
          const snapshot = await fetchForecastSnapshot(controller.signal);
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

          const fallback = getForecastMockSnapshot();
          setData(fallback);
          setDiagnostics(fallback.diagnostics ?? diagnostics);
          setLastUpdated(new Date().toISOString());
          setError(`${FALLBACK_DATA_MESSAGE} ${formatApiErrorMessage(loadError)}`);
        } finally {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        }
      };

      void run();
    }, 400);

    return () => {
      window.clearTimeout(timer);
      abortControllerRef.current?.abort();
    };
  }, [demoModeEnabled, reloadTick]);

  const simulateAction = async (type: "increase_ads" | "reduce_ads" | "restock") => {
    setSimulationLoading(true);
    try {
      const result = await simulateForecast({ type });
      setSimulation(result);
    } catch {
      setSimulation({
        status: "insufficient_data",
        recommendation: "Не удалось выполнить моделирование. Повторите после обновления данных.",
        confidence: null,
        expectedEffect: {},
        risks: []
      });
    } finally {
      setSimulationLoading(false);
    }
  };

  return {
    data,
    loading,
    error,
    reload,
    lastUpdated,
    diagnostics,
    simulation,
    simulationLoading,
    simulateAction
  };
}
