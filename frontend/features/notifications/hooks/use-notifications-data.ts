"use client";

import { useEffect, useRef, useState } from "react";
import type { NotificationChannelItem, NotificationTestResult, NotificationsSnapshot } from "@/features/notifications/types";
import {
  fetchNotificationsSnapshot,
  getNotificationsMockSnapshot,
  testNotificationChannel,
  updateNotificationRule
} from "@/features/notifications/services/notifications-data";
import { FALLBACK_DATA_MESSAGE, formatApiErrorMessage } from "@/shared/api";
import { getDemoNotificationsSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";
import type { WorkspaceDiagnostics } from "@/shared/api";

export function useNotificationsData() {
  const { enabled: demoModeEnabled } = useDemoMode();
  const initialData = getNotificationsMockSnapshot();
  const [data, setData] = useState<NotificationsSnapshot>(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState(false);
  const [lastTestResult, setLastTestResult] = useState<NotificationTestResult | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(initialData.lastUpdated ?? null);
  const [diagnostics, setDiagnostics] = useState<WorkspaceDiagnostics>(
    initialData.diagnostics ?? {
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
    const timer = window.setTimeout(() => {
      const controller = new AbortController();
      abortControllerRef.current?.abort();
      abortControllerRef.current = controller;

      const run = async () => {
        setLoading(true);
        setError(null);
        try {
          const snapshot = demoModeEnabled
            ? getDemoNotificationsSnapshot()
            : await fetchNotificationsSnapshot(controller.signal);
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
          const fallbackSnapshot = getNotificationsMockSnapshot();
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
    }, 500);

    return () => {
      window.clearTimeout(timer);
      abortControllerRef.current?.abort();
    };
  }, [demoModeEnabled, reloadTick]);

  const sendTest = async (channel: NotificationChannelItem["type"]) => {
    setPendingAction(true);
    setActionMessage(null);
    try {
      if (demoModeEnabled) {
        const fakeResult: NotificationTestResult = {
          id: `demo-test-${channel}`,
          channel,
          status: channel === "in_app" || channel === "webhook" ? "sent" : "failed",
          target: `${channel}-demo-target`,
          message: "Demo notification result.",
          simulated: true
        };
        setLastTestResult(fakeResult);
        setActionMessage(`Demo test notification via ${channel} completed with status ${fakeResult.status}.`);
      } else {
        const result = await testNotificationChannel({ channel });
        setLastTestResult(result);
        setActionMessage(`Test notification via ${channel} completed with status ${result.status}.`);
      }
      reload();
    } catch (actionError) {
      setActionMessage(formatApiErrorMessage(actionError));
    } finally {
      setPendingAction(false);
    }
  };

  const toggleRule = async (ruleId: string, enabled: boolean) => {
    setPendingAction(true);
    setActionMessage(null);
    try {
      if (demoModeEnabled) {
        setActionMessage(`Demo rule ${enabled ? "enabled" : "muted"} for ${ruleId}.`);
      } else {
        const updatedRule = await updateNotificationRule(ruleId, { enabled });
        setActionMessage(`${updatedRule.name} is now ${updatedRule.enabled ? "enabled" : "muted"}.`);
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
    lastTestResult,
    reload,
    lastUpdated,
    diagnostics,
    sendTest,
    toggleRule
  };
}
