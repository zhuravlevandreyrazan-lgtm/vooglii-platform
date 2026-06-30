"use client";

import Link from "next/link";
import { SettingsNav } from "@/app/settings/settings-nav";
import { useAuth } from "@/features/auth";
import { PageHeader } from "@/shared/layout";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";

function formatDate(value?: string | null) {
  if (!value) {
    return "Not synced yet";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function mapQualityScore(label?: string) {
  switch ((label ?? "").toLowerCase()) {
    case "high":
    case "showcase":
      return 90;
    case "medium":
      return 70;
    case "pending":
      return 50;
    default:
      return 60;
  }
}

export default function SettingsProfilePage() {
  const { authenticated, cabinet, context, diagnostics, error, loading, organization, user } = useAuth();

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Settings", "Profile"]}
        subtitle="A compact identity, organization, and Wildberries cabinet summary for beta onboarding and operator checks."
        title="Profile"
      />

      <SettingsNav />

      <div className="flex flex-wrap gap-2">
        <StatusBadge tone={authenticated ? "healthy" : "watch"}>
          {authenticated ? "Authenticated" : "Guest"}
        </StatusBadge>
        {context ? <StatusBadge tone="accent">Mode {context.mode}</StatusBadge> : null}
        {diagnostics ? <StatusBadge tone="neutral">Source {diagnostics.source}</StatusBadge> : null}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <WidgetCard
          error={error}
          loading={loading}
          status={user ? { label: user.role, tone: "accent" } : undefined}
          subtitle={user?.name ?? "Account profile"}
          title="User"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Email</p>
              <p className="mt-2 text-sm font-semibold">{user?.email ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Created</p>
              <p className="mt-2 text-sm font-semibold">{formatDate(user?.createdAt)}</p>
            </div>
          </div>
        </WidgetCard>

        <WidgetCard
          loading={loading}
          status={organization ? { label: organization.plan, tone: "healthy" } : undefined}
          subtitle={organization?.name ?? "Organization profile"}
          title="Organization"
        >
          <div className="space-y-4">
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Status</p>
              <p className="mt-2 text-sm font-semibold">{organization?.status ?? "n/a"}</p>
            </div>
            <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Created</p>
              <p className="mt-2 text-sm font-semibold">{formatDate(organization?.createdAt)}</p>
            </div>
          </div>
        </WidgetCard>
      </div>

      <WidgetCard
        loading={loading}
        status={cabinet ? { label: cabinet.connected ? "Connected" : "Disconnected", tone: cabinet.connected ? "healthy" : "watch" } : undefined}
        subtitle={cabinet?.name ?? "WB cabinet profile"}
        title="Wildberries Cabinet"
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Seller ID</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.sellerId ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Token Status</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.tokenStatus ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Last Sync</p>
            <p className="mt-2 text-sm font-semibold">{formatDate(cabinet?.lastSyncAt)}</p>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Cabinet Status</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.status ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Data Quality</p>
            <div className="mt-2">
              <HealthBadge label={cabinet?.dataQuality ?? "Unknown"} score={mapQualityScore(cabinet?.dataQuality)} />
            </div>
          </div>
          <div className="rounded-[22px] border border-[var(--line)] bg-white/75 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Workspace Context</p>
            <p className="mt-2 text-sm font-semibold">
              {context?.organizationId ?? "n/a"} / {context?.cabinetId ?? "n/a"}
            </p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            className="inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/wb-cabinet"
          >
            Open WB Cabinet Controls
          </Link>
        </div>
      </WidgetCard>
    </div>
  );
}
