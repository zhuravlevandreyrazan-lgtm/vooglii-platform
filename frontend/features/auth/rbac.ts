import type { PlatformPermission, PlatformRole } from "@/features/auth/types";

export const ROLE_PERMISSIONS: Record<PlatformRole, PlatformPermission[]> = {
  viewer: ["dashboard:view", "reports:view"],
  analyst: ["dashboard:view", "reports:view", "analytics:view", "ads:view", "finance:view"],
  manager: ["dashboard:view", "reports:view", "analytics:view", "ads:view", "finance:view", "users:view"],
  admin: [
    "dashboard:view",
    "reports:view",
    "analytics:view",
    "ads:view",
    "finance:view",
    "users:view",
    "users:manage",
    "settings:manage"
  ],
  owner: [
    "dashboard:view",
    "reports:view",
    "analytics:view",
    "ads:view",
    "finance:view",
    "users:view",
    "users:manage",
    "settings:manage"
  ]
};

export function getRolePermissions(role: PlatformRole) {
  return ROLE_PERMISSIONS[role] ?? [];
}

export function hasPermission(permissions: string[] | undefined | null, permission: PlatformPermission) {
  return (permissions ?? []).includes(permission);
}

export function hasAnyPermission(permissions: string[] | undefined | null, required: PlatformPermission[] | undefined) {
  if (!required || required.length === 0) {
    return true;
  }
  return required.some((permission) => hasPermission(permissions, permission));
}
