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
    label: "Главная",
    href: "/executive",
    description: "Ключевые показатели, риски, задачи и общая картина по кабинету.",
    icon: LayoutDashboard,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Бизнес",
    href: "/business",
    description: "Выручка, прибыль, маржинальность и бизнес-сигналы.",
    icon: BriefcaseBusiness,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Финансы",
    href: "/finance",
    description: "Качество прибыли, выплаты и финансовая прозрачность.",
    icon: BarChart3,
    requiredPermissions: ["finance:view"]
  },
  {
    label: "Реклама",
    href: "/advertising",
    description: "Расходы, эффективность кампаний и контроль роста.",
    icon: Megaphone,
    requiredPermissions: ["ads:view"]
  },
  {
    label: "Товары",
    href: "/products",
    description: "SKU, ассортимент, риски и готовность к росту.",
    icon: Boxes,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Остатки",
    href: "/inventory",
    description: "Покрытие остатков, пополнение и стабильность поставок.",
    icon: Blocks,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Автоматизация",
    href: "/automation",
    description: "Выгрузки, расписания, фоновые задачи и автоматизация.",
    icon: Cable,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Уведомления",
    href: "/notifications",
    description: "Каналы, правила, история и контроль доставки.",
    icon: Bell,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Отчеты",
    href: "/reports",
    description: "Экспорт, подборки для руководителя и история отчетов.",
    icon: FileText,
    requiredPermissions: ["reports:view"]
  },
  {
    label: "ИИ-советник",
    href: "/advisor",
    description: "Подсказки по решениям и сценарии управленческих действий.",
    icon: Bot,
    requiredPermissions: ["analytics:view"]
  },
  {
    label: "Команда",
    href: "/team",
    description: "Пользователи, роли, права доступа и управление командой.",
    icon: Users,
    requiredPermissions: ["users:view"]
  },
  {
    label: "Настройки",
    href: "/settings",
    description: "Параметры, интеграции и управление рабочим пространством.",
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
      breadcrumb: ["Платформа", match.label]
    };
  }

  return {
    title: "Платформа",
    description: "Коммерческая рабочая среда VOOGLII.",
    breadcrumb: ["Платформа"]
  };
}
