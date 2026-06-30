import type { WorkspaceDiagnostics } from "@/shared/api";
import type { StatusTone } from "@/types/platform";

export type NotificationChannelType = "telegram" | "email" | "webhook" | "in_app";

export type NotificationChannelItem = {
  id: string;
  type: NotificationChannelType;
  status: string;
  connected: boolean;
  lastTestAt: string | null;
  deliveryHealth: string;
  setupAction: string | null;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type NotificationRuleItem = {
  id: string;
  name: string;
  enabled: boolean;
  channel: NotificationChannelType;
  severity: string;
  trigger: string;
  schedule: string;
  owner: string;
  lastTriggeredAt: string | null;
  deepLink: string | null;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type NotificationHistoryItem = {
  id: string;
  title: string;
  channel: NotificationChannelType;
  status: string;
  time: string;
  target: string;
  relatedWorkspace: string | null;
  error: string | null;
  deepLink: string | null;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type NotificationOverview = {
  enabledRules: number;
  mutedRules: number;
  failedDeliveries: number;
  lastDelivery: string | null;
  activeChannels: number;
  health: string;
};

export type NotificationTestResult = {
  id: string;
  channel: NotificationChannelType;
  status: string;
  target: string;
  message: string;
  simulated: boolean;
  organizationName?: string | null;
  cabinetName?: string | null;
};

export type NotificationQuickStat = {
  label: string;
  value: string | number;
  tone: StatusTone;
};

export type NotificationsSnapshot = {
  overview: NotificationOverview;
  channels: NotificationChannelItem[];
  rules: NotificationRuleItem[];
  history: NotificationHistoryItem[];
  unreadCount: number;
  quickStats: NotificationQuickStat[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
