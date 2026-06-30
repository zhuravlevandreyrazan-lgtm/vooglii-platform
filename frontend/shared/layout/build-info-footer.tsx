"use client";

import { useEffect, useState } from "react";
import { apiEndpoints, requestJson } from "@/shared/api";

type VersionPayload = {
  version?: string;
  build?: string;
  git?: string;
  environment?: string;
  buildType?: string;
};

export function BuildInfoFooter() {
  const [version, setVersion] = useState<VersionPayload | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const payload = await requestJson<VersionPayload>(apiEndpoints.version);
        setVersion(payload);
      } catch {
        setVersion(null);
      }
    };
    void run();
  }, []);

  return (
    <span className="text-xs text-[var(--ink-soft)]">
      {version
        ? `v${version.version ?? "n/a"} • ${version.environment ?? "unknown"} • ${version.buildType ?? "build"} • ${version.git ?? "unknown"}`
        : "Build info unavailable"}
    </span>
  );
}
