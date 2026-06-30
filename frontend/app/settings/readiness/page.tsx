"use client";

import { useEffect, useState } from "react";
import { SettingsNav } from "@/app/settings/settings-nav";
import { apiEndpoints, formatApiErrorMessage, requestJson, RuntimeBadge } from "@/shared/api";
import { useDemoMode } from "@/shared/demo/demo-provider";
import { PageHeader } from "@/shared/layout";
import { StatusBadge } from "@/shared/status";
import { useWorkspaceContext } from "@/shared/workspace-context";
import { WidgetCard } from "@/shared/widgets";

type StatusPayload = {
  status?: string;
  version?: string;
  build?: string;
  wbApi?: string;
  database?: string;
  analytics?: string;
  ads?: string;
  finance?: string;
  system?: string;
  runtime?: {
    duration_ms?: number;
    cached?: boolean;
    stale?: boolean;
    degraded?: boolean;
    source?: string;
  };
};

type VersionPayload = {
  version?: string;
  build?: string;
  git?: string;
  apiVersion?: string;
  environment?: string;
  buildType?: string;
  frontendVersion?: string;
};

type HealthPayload = {
  status?: string;
  uptimeSeconds?: number;
  memoryUsageMb?: number | null;
  pythonVersion?: string;
  platform?: string;
  applicationVersion?: string;
  frontendVersion?: string;
  environment?: string;
  runtimeMode?: string;
  startup?: {
    ok?: boolean;
    warnings?: string[];
  };
};

type MetricsPayload = {
  startupValidation?: {
    ok?: boolean;
    warnings?: string[];
  };
};

const WORKSPACE_READINESS = [
  "Executive",
  "Business",
  "Finance",
  "Advertising",
  "Products",
  "Inventory",
  "Advisor",
  "Reports",
  "Product Drilldown"
];

const KNOWN_LIMITATIONS = [
  "Demo Mode is frontend-driven and does not persist server-side state.",
  "Automation exports, schedules, and notifications use placeholder delivery flows in dev/RC.",
  "Smoke status is still recorded manually after script execution."
];

export default function SettingsReadinessPage() {
  const { enabled: demoModeEnabled } = useDemoMode();
  const workspace = useWorkspaceContext();
  const [statusData, setStatusData] = useState<StatusPayload | null>(null);
  const [versionData, setVersionData] = useState<VersionPayload | null>(null);
  const [healthData, setHealthData] = useState<HealthPayload | null>(null);
  const [metricsData, setMetricsData] = useState<MetricsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const [statusPayload, versionPayload, healthPayload, metricsPayload] = await Promise.all([
          requestJson<StatusPayload>(apiEndpoints.status),
          requestJson<VersionPayload>(apiEndpoints.version),
          requestJson<HealthPayload>("/api/health"),
          requestJson<MetricsPayload>("/api/metrics")
        ]);
        setStatusData(statusPayload);
        setVersionData(versionPayload);
        setHealthData(healthPayload);
        setMetricsData(metricsPayload);
      } catch (loadError) {
        setError(formatApiErrorMessage(loadError));
      }
    };
    void run();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Settings", "Readiness"]}
        subtitle="A compact release checklist for demo sessions, smoke confidence, backend availability, and current platform mode."
        title="Release Readiness"
      />

      <SettingsNav />

      {statusData?.runtime ? (
        <RuntimeBadge
          context={{
            organization: workspace.organization?.name,
            cabinet: workspace.cabinet?.name,
            mode: workspace.mode
          }}
          diagnostics={{
            source: demoModeEnabled ? "demo" : ((statusData.runtime.source as "live" | "cache" | "stale_cache" | "degraded" | "fallback" | "demo") ?? "fallback"),
            degraded: Boolean(statusData.runtime.degraded),
            cached: Boolean(statusData.runtime.cached),
            stale: Boolean(statusData.runtime.stale),
            durationMs: statusData.runtime.duration_ms,
            validationStatus: "ok"
          }}
        />
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard error={error} subtitle="Platform mode" title="Environment">
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={demoModeEnabled ? "accent" : "healthy"}>
              {demoModeEnabled ? "DEMO MODE" : "LIVE MODE"}
            </StatusBadge>
            <StatusBadge tone="neutral">Backend API {statusData?.status ?? "Unknown"}</StatusBadge>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Version</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.version ?? statusData?.version ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Build</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.build ?? statusData?.build ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Commit</p>
              <p className="mt-2 font-mono text-[var(--ink-soft)]">{versionData?.git ?? "unknown"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">API</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.apiVersion ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Environment</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.environment ?? healthData?.environment ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Build Type</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.buildType ?? "n/a"}</p>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard subtitle="Last smoke status" title="Operational checks">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Smoke placeholder</p>
              <p className="mt-2 text-[var(--ink-soft)]">
                Run `python scripts/smoke_api.py`, `npm.cmd run type-check`, and `npm.cmd run build` before each RC demo.
              </p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Known limitations</p>
              <p className="mt-2 text-[var(--ink-soft)]">See `KNOWN_LIMITATIONS.md` for the current RC limitation list.</p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <WidgetCard subtitle="Workspace readiness" title="Showcase coverage">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {WORKSPACE_READINESS.map((workspace) => (
            <div key={workspace} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold">{workspace}</p>
                <StatusBadge tone="healthy">Ready</StatusBadge>
              </div>
            </div>
          ))}
        </div>
      </WidgetCard>

      <WidgetCard subtitle="Multi-tenant shell context" title="Workspace Context">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Organization Count</p>
            <p className="mt-2 text-sm font-semibold">{workspace.context.organizationCount}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Cabinet Count</p>
            <p className="mt-2 text-sm font-semibold">{workspace.context.cabinetCount}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Current Organization</p>
            <p className="mt-2 text-sm font-semibold">{workspace.organization?.name ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Current Cabinet</p>
            <p className="mt-2 text-sm font-semibold">{workspace.cabinet?.name ?? "n/a"}</p>
          </div>
        </div>
      </WidgetCard>

      <WidgetCard subtitle="Backend API status" title="Connected services">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[
            ["WB API", statusData?.wbApi],
            ["Database", statusData?.database],
            ["Analytics", statusData?.analytics],
            ["Ads", statusData?.ads],
            ["Finance", statusData?.finance],
            ["System", statusData?.system]
          ].map(([label, value]) => (
            <div key={label} className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">{label}</p>
              <p className="mt-2 text-sm font-semibold">{value ?? "Unknown"}</p>
            </div>
          ))}
        </div>
      </WidgetCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <WidgetCard subtitle="Runtime and startup checks" title="Health">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Uptime</p>
              <p className="mt-2 text-[var(--ink-soft)]">{typeof healthData?.uptimeSeconds === "number" ? `${healthData.uptimeSeconds}s` : "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Memory</p>
              <p className="mt-2 text-[var(--ink-soft)]">{typeof healthData?.memoryUsageMb === "number" ? `${healthData.memoryUsageMb} MB` : "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Python</p>
              <p className="mt-2 text-[var(--ink-soft)]">{healthData?.pythonVersion ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4 text-sm">
              <p className="font-semibold">Frontend</p>
              <p className="mt-2 text-[var(--ink-soft)]">{versionData?.frontendVersion ?? healthData?.frontendVersion ?? "n/a"}</p>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard subtitle="Deployment surface" title="Docker & Startup">
          <div className="grid gap-3">
            <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm">
              <p className="font-semibold">Docker</p>
              <p className="mt-2 text-[var(--ink-soft)]">Repository now includes multi-stage backend/frontend Dockerfiles and compose definitions.</p>
            </div>
            <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm">
              <p className="font-semibold">Startup Validation</p>
              <p className="mt-2 text-[var(--ink-soft)]">
                {metricsData?.startupValidation?.ok ? "Startup validation is passing." : "Startup validation returned warnings."}
              </p>
            </div>
            <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm">
              <p className="font-semibold">Deployment Status</p>
              <p className="mt-2 text-[var(--ink-soft)]">Ready for VPS/cloud deployment with environment-specific examples and CI build validation.</p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <WidgetCard subtitle="Workspace services" title="Automation">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Exports, schedules, and jobs are present with production-facing container and env preparation.
          </p>
        </WidgetCard>
        <WidgetCard subtitle="Workspace services" title="Notifications">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Notifications runtime is observable and delivery placeholders remain safely separated from production secrets.
          </p>
        </WidgetCard>
        <WidgetCard subtitle="Workspace services" title="Auth">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Auth, organization, and cabinet context remain available and visible through startup, health, and readiness surfaces.
          </p>
        </WidgetCard>
      </div>

      <WidgetCard subtitle="Release candidate notes" title="Known limitations">
        <div className="grid gap-3">
          {KNOWN_LIMITATIONS.map((item) => (
            <div key={item} className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4 text-sm text-[var(--ink-soft)]">
              {item}
            </div>
          ))}
        </div>
      </WidgetCard>
    </div>
  );
}
