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
    description: "Ключевые показатели, риски и приоритеты.",
    icon: LayoutDashboard,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Бизнес",
    href: "/business",
    description: "Выручка, прибыль и сигналы бизнеса.",
    icon: BriefcaseBusiness,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Финансы",
    href: "/finance",
    description: "Выплаты, прибыль и прозрачность данных.",
    icon: BarChart3,
    requiredPermissions: ["finance:view"]
  },
  {
    label: "Реклама",
    href: "/advertising",
    description: "Расходы, эффективность и контроль кампаний.",
    icon: Megaphone,
    requiredPermissions: ["ads:view"]
  },
  {
    label: "Товары",
    href: "/products",
    description: "SKU, ассортимент и точки роста.",
    icon: Boxes,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Остатки",
    href: "/inventory",
    description: "Остатки, пополнение и стабильность поставок.",
    icon: Blocks,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Автоматизация",
    href: "/automation",
    description: "Выгрузки, расписания и фоновые задачи.",
    icon: Cable,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Уведомления",
    href: "/notifications",
    description: "Каналы, правила и история доставки.",
    icon: Bell,
    requiredPermissions: ["dashboard:view"]
  },
  {
    label: "Отчеты",
    href: "/reports",
    description: "Экспорт, подборки и история отчетов.",
    icon: FileText,
    requiredPermissions: ["reports:view"]
  },
  {
    label: "ИИ-советник",
    href: "/advisor",
    description: "Подсказки по решениям и сценарии действий.",
    icon: Bot,
    requiredPermissions: ["analytics:view"]
  },
  {
    label: "Команда",
    href: "/team",
    description: "Пользователи, роли и доступы.",
    icon: Users,
    requiredPermissions: ["users:view"]
  },
  {
    label: "Настройки",
    href: "/settings",
    description: "Параметры, интеграции и рабочее пространство.",
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
