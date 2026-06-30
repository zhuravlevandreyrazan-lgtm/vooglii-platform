"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchProductDetailsSnapshot,
  getProductDetailsMockSnapshot
} from "@/features/product-details/services/product-details-data";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { getDemoProductDetailsSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type { WorkspaceDiagnostics } from "@/shared/api";
import type { ProductDetailsSnapshot } from "@/features/product-details/types";

export type UseProductDetailsDataResult = {
  data: ProductDetailsSnapshot;
  loading: boolean;
  error: string | null;
  reload: () => void;
  lastUpdated: string | null;
  diagnostics: WorkspaceDiagnostics;
};

export function useProductDetailsData(sku: string): UseProductDetailsDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const initialData = getProductDetailsMockSnapshot(sku);
  const fallbackDiagnostics =
    initialData.diagnostics ?? {
      source: "fallback",
      degraded: true,
      cached: false,
      stale: false,
      validationStatus: "fallback" as const
    };
  const [data, setData] = useState<ProductDetailsSnapshot>(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(initialData.lastUpdated ?? null);
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
      const demoSnapshot = getDemoProductDetailsSnapshot(sku);
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
          const snapshot = await fetchProductDetailsSnapshot(sku, controller.signal);

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

          const fallbackSnapshot = getProductDetailsMockSnapshot(sku);
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
  }, [demoModeEnabled, reloadTick, sku]);

  return {
    data,
    loading,
    error,
    reload,
    lastUpdated,
    diagnostics
  };
}
