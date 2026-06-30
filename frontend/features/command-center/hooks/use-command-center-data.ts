"use client";

import { useEffect, useRef, useState } from "react";
import { buildCommandCenterKpis } from "@/features/command-center/command-center-kpis";
import { buildExecutiveBrief } from "@/features/command-center/executive-brief";
import type { ExecutiveBrief } from "@/features/command-center/executive-brief-types";
import { buildExecutiveTimeline } from "@/features/command-center/executive-timeline";
import type { ExecutiveTimelineEvent } from "@/features/command-center/executive-timeline-types";
import type { CommandCenterKpis } from "@/features/command-center/kpi-types";
import { buildPriorityActions } from "@/features/command-center/priority-actions";
import type { PriorityAction } from "@/features/command-center/priority-actions-types";
import { formatApiErrorMessage } from "@/shared/api";
import { getDemoCommandCenterSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";
import {
  fetchCommandCenterApiSnapshot,
  getCommandCenterMockSnapshot,
} from "@/services/command-center-api";
import type { CommandCenterScreenData } from "@/types/platform";

export type UseCommandCenterDataResult = {
  data: CommandCenterScreenData;
  kpis: CommandCenterKpis;
  executiveBrief: ExecutiveBrief;
  priorityActions: PriorityAction[];
  executiveTimeline: ExecutiveTimelineEvent[];
  loading: boolean;
  error: string | null;
  reload: () => void;
  lastUpdated: string | null;
};

const INITIAL_DATA = getCommandCenterMockSnapshot();

export function useCommandCenterData(): UseCommandCenterDataResult {
  const { enabled: demoModeEnabled } = useDemoMode();
  const [data, setData] = useState<CommandCenterScreenData>(INITIAL_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const reloadTickRef = useRef(0);
  const [reloadTick, setReloadTick] = useState(0);

  const reload = () => {
    reloadTickRef.current += 1;
    setReloadTick(reloadTickRef.current);
  };
  const kpis = buildCommandCenterKpis(data.snapshot);
  const executiveBrief = buildExecutiveBrief(kpis);
  const priorityActions = buildPriorityActions(kpis, executiveBrief);
  const executiveTimeline = buildExecutiveTimeline(kpis, executiveBrief, priorityActions);

  useEffect(() => {
    if (demoModeEnabled) {
      const demoSnapshot = getDemoCommandCenterSnapshot();
      setLoading(false);
      setError(null);
      setData(demoSnapshot);
      setLastUpdated(new Date().toISOString());
      window.dispatchEvent(
        new CustomEvent("vooglii:command-center-source", {
          detail: {
            source: demoSnapshot.source
          }
        })
      );
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
          const nextData = await fetchCommandCenterApiSnapshot(controller.signal);

          if (controller.signal.aborted) {
            return;
          }

          setData(nextData);
          setError(null);
          setLastUpdated(new Date().toISOString());

          window.dispatchEvent(
            new CustomEvent("vooglii:command-center-source", {
              detail: {
                source: nextData.source
              }
            })
          );
        } catch (requestError) {
          if (controller.signal.aborted) {
            return;
          }

          const fallbackData: CommandCenterScreenData = {
            ...getCommandCenterMockSnapshot(),
            fallbackReason: formatApiErrorMessage(requestError)
          };

          setData(fallbackData);
          setError(formatApiErrorMessage(requestError));
          setLastUpdated(new Date().toISOString());
        } finally {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        }
      };

      void run();
    }, 1000);

    return () => {
      window.clearTimeout(timer);
      abortControllerRef.current?.abort();
    };
  }, [demoModeEnabled, reloadTick]);

  return {
    data,
    kpis,
    executiveBrief,
    priorityActions,
    executiveTimeline,
    loading,
    error,
    reload,
    lastUpdated
  };
}
