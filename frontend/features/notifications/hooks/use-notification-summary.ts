"use client";

import { useEffect, useState } from "react";
import { getNotificationsMockSnapshot } from "@/features/notifications/services/notifications-data";
import { apiEndpoints, assertWorkspacePayload, requestJson } from "@/shared/api";
import { getDemoNotificationsSnapshot } from "@/shared/demo/demo-data";
import { useDemoMode } from "@/shared/demo/demo-provider";

type NotificationSummaryState = {
  unreadCount: number;
};

function fallbackSummary(demoModeEnabled: boolean): NotificationSummaryState {
  const snapshot = demoModeEnabled ? getDemoNotificationsSnapshot() : getNotificationsMockSnapshot();
  return {
    unreadCount: snapshot.unreadCount
  };
}

export function useNotificationSummary() {
  const { enabled: demoModeEnabled } = useDemoMode();
  const [summary, setSummary] = useState<NotificationSummaryState>(() => fallbackSummary(demoModeEnabled));

  useEffect(() => {
    const controller = new AbortController();

    const run = async () => {
      if (demoModeEnabled) {
        setSummary(fallbackSummary(true));
        return;
      }

      try {
        const payload = await requestJson<unknown>(apiEndpoints.notifications, { signal: controller.signal });
        const record = assertWorkspacePayload(payload, apiEndpoints.notifications, "Notifications");
        const unreadCount = typeof record.unreadCount === "number" ? record.unreadCount : 0;
        if (!controller.signal.aborted) {
          setSummary({ unreadCount });
        }
      } catch {
        if (!controller.signal.aborted) {
          setSummary(fallbackSummary(false));
        }
      }
    };

    void run();

    return () => {
      controller.abort();
    };
  }, [demoModeEnabled]);

  return summary;
}
