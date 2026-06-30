"use client";

import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { useAuthSession } from "@/features/auth/hooks/use-auth-session";

type AuthContextValue = ReturnType<typeof useAuthSession>;

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const value = useAuthSession();
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
