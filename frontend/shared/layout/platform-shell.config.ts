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
  Settings
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type WorkspaceNavItem = {
  label: string;
  href: string;
  description: string;
  icon: LucideIcon;
};

export const workspaceNavigation: WorkspaceNavItem[] = [
  {
    label: "Executive",
    href: "/executive",
    description: "Leadership view, KPIs, risks, actions, and timeline.",
    icon: LayoutDashboard
  },
  {
    label: "Business",
    href: "/business",
    description: "Business health, revenue movement, and operating signals.",
    icon: BriefcaseBusiness
  },
  {
    label: "Finance",
    href: "/finance",
    description: "Profit quality, payout clarity, and finance explainability.",
    icon: BarChart3
  },
  {
    label: "Advertising",
    href: "/advertising",
    description: "Spend efficiency, campaigns, and growth control.",
    icon: Megaphone
  },
  {
    label: "Products",
    href: "/products",
    description: "SKU pressure, assortment movement, and readiness.",
    icon: Boxes
  },
  {
    label: "Inventory",
    href: "/inventory",
    description: "Stock coverage, replenishment, and supply stability.",
    icon: Blocks
  },
  {
    label: "Automation",
    href: "/automation",
    description: "Exports, schedules, jobs, and automation control.",
    icon: Cable
  },
  {
    label: "Notifications",
    href: "/notifications",
    description: "Channels, rules, history, and delivery testing.",
    icon: Bell
  },
  {
    label: "Reports",
    href: "/reports",
    description: "Exports, executive packs, and historical reporting.",
    icon: FileText
  },
  {
    label: "AI Advisor",
    href: "/advisor",
    description: "Explainable decision support and advisory workflows.",
    icon: Bot
  },
  {
    label: "Settings",
    href: "/settings",
    description: "Preferences, integrations, and workspace controls.",
    icon: Settings
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
