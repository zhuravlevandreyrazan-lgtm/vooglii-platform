import {
  Bot,
  BarChart3,
  Bell,
  Blocks,
  BriefcaseBusiness,
  Boxes,
  Cable,
  FileText,
  LayoutDashboard,
  Megaphone,
  Settings,
  Users
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { PlatformPermission } from "@/features/auth/types";

export type WorkspaceNavItem = {
  label: string;
  href: string;
  description: string;
  icon: LucideIcon;
  requiredPermissions?: PlatformPermission[];
};

export const workspaceNavigation: WorkspaceNavItem[] = [
  {
    label: "Executive",
    href: "/executive",
    description: "Leadership view, KPIs, risks, actions, and timeline.",
    icon: LayoutDashboard,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Business",
    href: "/business",
    description: "Business health, revenue movement, and operating signals.",
    icon: BriefcaseBusiness,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Finance",
    href: "/finance",
    description: "Profit quality, payout clarity, and finance explainability.",
    icon: BarChart3,
    requiredPermissions: ["finance:view"]
  },
  {
    label: "Advertising",
    href: "/advertising",
    description: "Spend efficiency, campaigns, and growth control.",
    icon: Megaphone,
    requiredPermissions: ["ads:view"]
  },
  {
    label: "Products",
    href: "/products",
    description: "SKU pressure, assortment movement, and readiness.",
    icon: Boxes,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Inventory",
    href: "/inventory",
    description: "Stock coverage, replenishment, and supply stability.",
    icon: Blocks,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Automation",
    href: "/automation",
    description: "Exports, schedules, jobs, and automation control.",
    icon: Cable,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Notifications",
    href: "/notifications",
    description: "Channels, rules, history, and delivery testing.",
    icon: Bell,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Reports",
    href: "/reports",
    description: "Exports, executive packs, and historical reporting.",
    icon: FileText,
    requiredPermissions: ["reports:view"]
  },
  {
    label: "AI Advisor",
    href: "/advisor",
    description: "Explainable decision support and advisory workflows.",
    icon: Bot,
    requiredPermissions: ["analytics:view"]
  },
  {
    label: "Team",
    href: "/team",
    description: "Roles, permissions, and user lifecycle controls.",
    icon: Users,
    requiredPermissions: ["users:view"]
  },
  {
    label: "Settings",
    href: "/settings",
    description: "Preferences, integrations, and workspace controls.",
    icon: Settings,
    requiredPermissions: ["settings:manage"]
  }
];

export function resolveWorkspaceMeta(pathname: string) {
  const match = workspaceNavigation.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  );

  if (match) {
    return {
      title: match.label,
      description: match.description,
      breadcrumb: ["Platform", match.label]
    };
  }

  return {
    title: "Platform",
    description: "VOOGLII platform workspace shell.",
    breadcrumb: ["Platform"]
  };
}
