"use client";

import { useState } from "react";
import { SettingsNav } from "@/app/settings/settings-nav";
import { connectWbCabinet, disconnectWbCabinet, useAuth } from "@/features/auth";
import { Button } from "@/shared/components/button";
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

function qualityScore(label?: string) {
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

export default function SettingsWbCabinetPage() {
  const { cabinet, context, error, loading, reload } = useAuth();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);

  const runAction = async (action: "connect" | "disconnect") => {
    setActionPending(true);
    setActionMessage(null);
    try {
      if (action === "connect") {
        const nextCabinet = await connectWbCabinet();
        setActionMessage(`Cabinet ${nextCabinet.name} responded with status ${nextCabinet.status}.`);
      } else {
        const nextCabinet = await disconnectWbCabinet();
        setActionMessage(`Cabinet ${nextCabinet.name} responded with status ${nextCabinet.status}.`);
      }
      await reload();
    } catch (actionError) {
      const message = actionError instanceof Error ? actionError.message : "Unable to complete cabinet action.";
      setActionMessage(message);
    } finally {
      setActionPending(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Settings", "WB Cabinet"]}
        subtitle="Safe cabinet diagnostics and UI-level connect or disconnect actions without exposing real Wildberries tokens to the frontend."
        title="WB Cabinet"
        actions={
          cabinet ? (
            <StatusBadge tone={cabinet.connected ? "healthy" : "watch"}>
              {cabinet.connected ? "Connected" : "Disconnected"}
            </StatusBadge>
          ) : null
        }
      />

      <SettingsNav />

      <WidgetCard
        error={error}
        loading={loading}
        status={context ? { label: context.mode, tone: context.mode === "demo" ? "accent" : "neutral" } : undefined}
        subtitle={cabinet?.name ?? "Cabinet profile"}
        title="Connection Status"
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Seller ID</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.sellerId ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Token Status</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.tokenStatus ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Last Sync</p>
            <p className="mt-2 text-sm font-semibold">{formatDate(cabinet?.lastSyncAt)}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Cabinet Status</p>
            <p className="mt-2 text-sm font-semibold">{cabinet?.status ?? "n/a"}</p>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Data Quality</p>
            <div className="mt-2">
              <HealthBadge label={cabinet?.dataQuality ?? "Unknown"} score={qualityScore(cabinet?.dataQuality)} />
            </div>
          </div>
          <div className="rounded-[22px] bg-[var(--panel-strong)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Workspace Context</p>
            <p className="mt-2 text-sm font-semibold">{context?.cabinetId ?? "n/a"}</p>
          </div>
        </div>

        <div className="mt-5 rounded-[22px] border border-[color:rgba(176,122,24,0.24)] bg-[color:rgba(176,122,24,0.08)] p-4 text-sm leading-7 text-[var(--ink)]">
          Do not paste real Wildberries tokens in demo or dev mode. Live token handling must remain
          backend-only over HTTPS in production.
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Button disabled={actionPending} onClick={() => void runAction("connect")}>
            Connect Cabinet
          </Button>
          <Button disabled={actionPending} variant="ghost" onClick={() => void runAction("disconnect")}>
            Disconnect Cabinet
          </Button>
          {actionMessage ? <StatusBadge tone="neutral">{actionMessage}</StatusBadge> : null}
        </div>
      </WidgetCard>
    </div>
  );
}
