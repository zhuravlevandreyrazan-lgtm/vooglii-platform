"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  applyDemoToSearchParams,
  DEMO_QUERY_PARAM,
  DEMO_STORAGE_KEY,
  isDemoQueryEnabled
} from "@/shared/demo/demo-mode";

type DemoModeContextValue = {
  enabled: boolean;
  ready: boolean;
  setDemoMode: (enabled: boolean) => void;
  toggleDemoMode: () => void;
};

const DemoModeContext = createContext<DemoModeContextValue | null>(null);

export function DemoModeProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [enabled, setEnabled] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const currentSearchParams =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search)
        : new URLSearchParams();
    const fromQuery = isDemoQueryEnabled(currentSearchParams.get(DEMO_QUERY_PARAM));
    const fromStorage =
      typeof window !== "undefined" &&
      window.sessionStorage.getItem(DEMO_STORAGE_KEY) === "true";
    const nextEnabled = fromQuery || fromStorage;
    setEnabled(nextEnabled);
    if (typeof window !== "undefined") {
      if (nextEnabled) {
        window.sessionStorage.setItem(DEMO_STORAGE_KEY, "true");
      } else {
        window.sessionStorage.removeItem(DEMO_STORAGE_KEY);
      }
    }
    setReady(true);
  }, [pathname]);

  const setDemoMode = (nextEnabled: boolean) => {
    if (typeof window !== "undefined") {
      if (nextEnabled) {
        window.sessionStorage.setItem(DEMO_STORAGE_KEY, "true");
      } else {
        window.sessionStorage.removeItem(DEMO_STORAGE_KEY);
      }
    }
    setEnabled(nextEnabled);
    const baseSearchParams =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search)
        : new URLSearchParams();
    const nextSearchParams = applyDemoToSearchParams(
      baseSearchParams,
      nextEnabled
    );
    const nextQuery = nextSearchParams.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname);
  };

  const value = useMemo<DemoModeContextValue>(
    () => ({
      enabled,
      ready,
      setDemoMode,
      toggleDemoMode: () => setDemoMode(!enabled)
    }),
    [enabled, ready]
  );

  return <DemoModeContext.Provider value={value}>{children}</DemoModeContext.Provider>;
}

export function useDemoMode() {
  const context = useContext(DemoModeContext);
  if (!context) {
    throw new Error("useDemoMode must be used inside DemoModeProvider.");
  }
  return context;
}
