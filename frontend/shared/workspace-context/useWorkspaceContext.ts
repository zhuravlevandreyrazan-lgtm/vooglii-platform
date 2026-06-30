"use client";

import { useContext } from "react";
import { WorkspaceContextReact } from "@/shared/workspace-context/workspace-context-provider";

export function useWorkspaceContext() {
  const context = useContext(WorkspaceContextReact);
  if (!context) {
    throw new Error("useWorkspaceContext must be used inside WorkspaceContextProvider.");
  }
  return context;
}
