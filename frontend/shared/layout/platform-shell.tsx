"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { AuthProvider } from "@/features/auth";
import { DemoModeProvider } from "@/shared/demo/demo-provider";
import { BuildInfoFooter } from "@/shared/layout/build-info-footer";
import { resolveWorkspaceMeta } from "@/shared/layout/platform-shell.config";
import { WorkspaceSidebar } from "@/shared/layout/workspace-sidebar";
import { WorkspaceTopBar } from "@/shared/layout/workspace-topbar";
import { WorkspaceContextProvider } from "@/shared/workspace-context";

export function PlatformShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | undefined>(undefined);
  const meta = resolveWorkspaceMeta(pathname);

  useEffect(() => {
    setLastUpdated(
      new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      }).format(new Date())
    );
  }, [pathname]);

  return (
    <DemoModeProvider>
      <WorkspaceContextProvider>
        <AuthProvider>
          <div className="shell-grid" data-collapsed={collapsed ? "true" : "false"}>
            <WorkspaceSidebar
              collapsed={collapsed}
              mobileOpen={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              onToggleCollapsed={() => setCollapsed((value) => !value)}
              pathname={pathname}
            />

            <div className="workspace-backdrop flex min-h-screen flex-col">
              <WorkspaceTopBar
                breadcrumb={meta.breadcrumb}
                lastUpdated={lastUpdated}
                onOpenSidebar={() => setSidebarOpen(true)}
                title={meta.title}
              />

              <main className="flex-1 px-4 py-6 lg:px-8 lg:py-8">{children}</main>

              <footer className="border-t border-[var(--line)] px-4 py-4 text-sm text-[var(--ink-soft)] lg:px-8">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                  <span>VOOGLII Platform Shell</span>
                  <span>Executive workspace architecture prepared for business, finance, advertising, and AI modules.</span>
                  <BuildInfoFooter />
                </div>
              </footer>
            </div>
          </div>
        </AuthProvider>
      </WorkspaceContextProvider>
    </DemoModeProvider>
  );
}
