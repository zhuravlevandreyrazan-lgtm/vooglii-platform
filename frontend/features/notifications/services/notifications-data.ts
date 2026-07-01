"use client";

import type {
  NotificationChannelItem,
  NotificationHistoryItem,
  NotificationQuickStat,
  NotificationRuleItem,
  NotificationTestResult,
  NotificationsSnapshot
} from "@/features/notifications/types";
import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";

type RawNotificationsRecord = {
  status?: {
    enabledRules?: number;
    mutedRules?: number;
    failedDeliveries?: number;
    lastDelivery?: string | null;
    activeChannels?: number;
    health?: string;
  };
  rules?: NotificationRuleItem[];
  channels?: NotificationChannelItem[];
  unreadCount?: number;
};

type RawChannelRecord = NotificationChannelItem;
type RawRuleRecord = NotificationRuleItem;
type RawHistoryRecord = NotificationHistoryItem;
type RawTestResponse = {
  delivery?: NotificationTestResult;
};

const MOCK_CHANNELS: NotificationChannelItem[] = [
  {
    id: "channel-telegram",
    type: "telegram",
    status: "pending",
    connected: false,
    lastTestAt: null,
    deliveryHealth: "Ожидает настройки",
    setupAction: "Подключите Telegram-канал уведомлений"
  },
  {
    id: "channel-email",
    type: "email",
    status: "pending",
    connected: false,
    lastTestAt: null,
    deliveryHealth: "Ожидает настройки",
    setupAction: "Настройте email-канал уведомлений"
  },
  {
    id: "channel-webhook",
    type: "webhook",
    status: "disabled",
    connected: false,
    lastTestAt: null,
    deliveryHealth: "Неактивно",
    setupAction: "Настройте webhook для уведомлений"
  },
  {
    id: "channel-in-app",
    type: "in_app",
    status: "enabled",
    connected: true,
    lastTestAt: "2026-06-30T11:20:00Z",
    deliveryHealth: "Норма",
    setupAction: "Откройте центр уведомлений"
  }
];

const MOCK_RULES: NotificationRuleItem[] = [
  {
    id: "notification-rule-ceo",
    name: "Ежедневный отчет для руководителя",
    enabled: true,
    channel: "in_app",
    severity: "info",
    trigger: "Публикация ежедневной управленческой сводки",
    schedule: "Ежедневно в 09:00 Europe/Moscow",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: "2026-06-30T09:00:00Z",
    deepLink: "/executive"
  },
  {
    id: "notification-rule-profit",
    name: "Падение прибыли",
    enabled: true,
    channel: "telegram",
    severity: "high",
    trigger: "Операционная прибыль падает более чем на 10% неделя к неделе",
    schedule: "По событию",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: "2026-06-30T10:12:00Z",
    deepLink: "/finance"
  },
  {
    id: "notification-rule-stock",
    name: "Риск потери продаж из-за остатков",
    enabled: true,
    channel: "in_app",
    severity: "high",
    trigger: "Покрытие запасов опускается ниже порога",
    schedule: "Каждые 2 часа",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: "2026-06-30T08:25:00Z",
    deepLink: "/inventory"
  },
  {
    id: "notification-rule-ads",
    name: "Рост рекламных расходов",
    enabled: true,
    channel: "email",
    severity: "medium",
    trigger: "Расходы превышают дневной план эффективности",
    schedule: "По событию",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: "2026-06-30T10:35:00Z",
    deepLink: "/advertising"
  },
  {
    id: "notification-rule-quality",
    name: "Качество финансовых данных",
    enabled: false,
    channel: "in_app",
    severity: "muted",
    trigger: "Надежность финансовых данных падает ниже 80%",
    schedule: "После обновления финансов",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: null,
    deepLink: "/finance"
  },
  {
    id: "notification-rule-weekly",
    name: "Еженедельный отчет",
    enabled: true,
    channel: "email",
    severity: "info",
    trigger: "Пакет еженедельных отчетов готов",
    schedule: "По понедельникам в 08:00",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: "2026-06-30T08:00:00Z",
    deepLink: "/reports"
  },
  {
    id: "notification-rule-advisor",
    name: "Критичная рекомендация ИИ-советника",
    enabled: true,
    channel: "in_app",
    severity: "critical",
    trigger: "ИИ-советник сформировал критичную рекомендацию",
    schedule: "По событию",
    owner: "Daria Kuznetsova",
    lastTriggeredAt: "2026-06-30T11:10:00Z",
    deepLink: "/advisor"
  }
];

const MOCK_HISTORY: NotificationHistoryItem[] = [
  {
    id: "notification-history-1",
    title: "Ежедневная сводка готова",
    channel: "in_app",
    status: "sent",
    time: "2026-06-30T09:00:12Z",
    target: "Входящие руководителя",
    relatedWorkspace: "executive",
    error: null,
    deepLink: "/executive"
  },
  {
    id: "notification-history-2",
    title: "Сигнал о падении прибыли",
    channel: "telegram",
    status: "failed",
    time: "2026-06-30T10:12:00Z",
    target: "Telegram",
    relatedWorkspace: "finance",
    error: "Доставка уведомлений в этой среде отключена.",
    deepLink: "/finance"
  },
  {
    id: "notification-history-3",
    title: "Еженедельный отчет подготовлен",
    channel: "email",
    status: "pending",
    time: "2026-06-30T11:18:00Z",
    target: "Email",
    relatedWorkspace: "reports",
    error: null,
    deepLink: "/reports"
  }
];

function buildQuickStats(snapshot: NotificationsSnapshot): NotificationQuickStat[] {
  const healthTone = snapshot.overview.health === "Healthy" ? "healthy" : "watch";
  return [
    { label: "Непрочитанные", value: snapshot.unreadCount, tone: "accent" as const },
    { label: "Активные правила", value: snapshot.overview.enabledRules, tone: "healthy" as const },
    { label: "Ошибки доставки", value: snapshot.overview.failedDeliveries, tone: "watch" as const },
    { label: "Состояние", value: snapshot.overview.health, tone: healthTone }
  ];
}

export function normalizeNotificationsSnapshot(
  raw: {
    overview?: RawNotificationsRecord["status"];
    channels?: NotificationChannelItem[];
    rules?: NotificationRuleItem[];
    history?: NotificationHistoryItem[];
    unreadCount?: number;
    lastUpdated?: string | null;
  },
  diagnostics = createFallbackDiagnostics()
): NotificationsSnapshot {
  const snapshot: NotificationsSnapshot = {
    overview: {
      enabledRules: raw.overview?.enabledRules ?? 0,
      mutedRules: raw.overview?.mutedRules ?? 0,
      failedDeliveries: raw.overview?.failedDeliveries ?? 0,
      lastDelivery: raw.overview?.lastDelivery ?? null,
      activeChannels: raw.overview?.activeChannels ?? 0,
      health: raw.overview?.health ?? "Unknown"
    },
    channels: raw.channels ?? [],
    rules: raw.rules ?? [],
    history: raw.history ?? [],
    unreadCount: raw.unreadCount ?? 0,
    quickStats: [],
    lastUpdated: raw.lastUpdated ?? new Date().toISOString(),
    diagnostics
  };

  snapshot.quickStats = buildQuickStats(snapshot);
  return snapshot;
}

export function getNotificationsMockSnapshot() {
  return normalizeNotificationsSnapshot({
    overview: {
      enabledRules: 6,
      mutedRules: 1,
      failedDeliveries: 1,
      lastDelivery: MOCK_HISTORY[0]?.time ?? null,
      activeChannels: 1,
      health: "Watch"
    },
    channels: MOCK_CHANNELS,
    rules: MOCK_RULES,
    history: MOCK_HISTORY,
    unreadCount: 2,
    lastUpdated: "2026-06-30T11:20:00Z"
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function fetchNotificationsSnapshot(signal?: AbortSignal) {
  const [summaryPayload, historyPayload, channelsPayload] = await Promise.all([
    requestJson<unknown>(apiEndpoints.notifications, { signal }),
    requestJson<unknown>(apiEndpoints.notificationHistory, { signal }),
    requestJson<unknown>(apiEndpoints.notificationChannels, { signal })
  ]);

  const summaryRecord = assertWorkspacePayload(summaryPayload, apiEndpoints.notifications, "Notifications");
  const historyRecord = assertWorkspacePayload(historyPayload, apiEndpoints.notificationHistory, "Notification History");
  const channelsRecord = assertWorkspacePayload(channelsPayload, apiEndpoints.notificationChannels, "Notification Channels");

  if (!isRecord(summaryRecord) || !isRecord(historyRecord) || !isRecord(channelsRecord)) {
    throw new ApiError("Notifications API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.notifications
    });
  }

  const runtime =
    normalizeRuntimeMetadata(summaryRecord) ??
    normalizeRuntimeMetadata(historyRecord) ??
    normalizeRuntimeMetadata(channelsRecord);

  return normalizeNotificationsSnapshot(
    {
      overview: isRecord(summaryRecord.status) ? (summaryRecord.status as RawNotificationsRecord["status"]) : undefined,
      channels: Array.isArray(channelsRecord.channels) ? (channelsRecord.channels as RawChannelRecord[]) : [],
      rules: Array.isArray(summaryRecord.rules) ? (summaryRecord.rules as RawRuleRecord[]) : [],
      history: Array.isArray(historyRecord.history) ? (historyRecord.history as RawHistoryRecord[]) : [],
      unreadCount: typeof summaryRecord.unreadCount === "number" ? summaryRecord.unreadCount : 0,
      lastUpdated: new Date().toISOString()
    },
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}

export async function testNotificationChannel(payload: {
  channel: NotificationChannelItem["type"];
  target?: string;
  message?: string;
}) {
  const response = await requestJson<unknown>(apiEndpoints.notificationTest, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const record = assertWorkspacePayload(response, apiEndpoints.notificationTest, "Notification Test");
  const delivery = isRecord(record.delivery) ? (record.delivery as RawTestResponse["delivery"]) : null;
  if (!delivery) {
    throw new ApiError("Notification test payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.notificationTest
    });
  }
  return delivery;
}

export async function updateNotificationRule(ruleId: string, payload: Record<string, unknown>) {
  const response = await requestJson<unknown>(`${apiEndpoints.notificationRules}/${ruleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const record = assertWorkspacePayload(response, `${apiEndpoints.notificationRules}/${ruleId}`, "Notification Rule Update");
  const rule = isRecord(record.rule) ? (record.rule as NotificationRuleItem) : null;
  if (!rule) {
    throw new ApiError("Notification rule update payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: `${apiEndpoints.notificationRules}/${ruleId}`
    });
  }
  return rule;
}
