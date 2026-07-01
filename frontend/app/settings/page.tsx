import Link from "next/link";
import { SettingsNav } from "@/app/settings/settings-nav";
import { PageHeader } from "@/shared/layout";
import { WidgetCard } from "@/shared/widgets";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={["Platform", "Settings"]}
        subtitle="Workspace preferences, release controls, profile visibility, and cabinet diagnostics for the closed beta phase."
        title="Settings"
      />

      <SettingsNav />

      <div className="grid gap-6 xl:grid-cols-4">
        <WidgetCard subtitle="Release Readiness" title="Launch controls">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Review backend availability, live versus demo mode, version information, and known
            limitations before showing the platform to new users.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/readiness"
          >
            Open Readiness Page
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="User, organization, and cabinet summary" title="Profile">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            See the current dev or demo session, organization plan, seller cabinet, token status,
            and sync quality in one place.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/profile"
          >
            Open Profile Page
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Connection controls and safe placeholders" title="WB Cabinet">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Demo Mode can be enabled from the top bar in development, while cabinet connect and
            disconnect remain UI-safe and backend-owned.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/settings/wb-cabinet"
          >
            Open Cabinet Page
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Channels, rules, and safe delivery testing" title="Notifications">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Manage notification routing, in-app delivery visibility, and placeholder test delivery
            without exposing Telegram, email, or webhook secrets to the frontend.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/notifications"
          >
            Open Notifications Hub
          </Link>
        </WidgetCard>

        <WidgetCard subtitle="Roles, permissions, and audit visibility" title="Team">
          <p className="text-sm leading-7 text-[var(--ink-soft)]">
            Review platform roles, understand access boundaries, and use backend-owned user
            lifecycle actions without exposing secrets or deploy-only controls in the frontend.
          </p>
          <Link
            className="mt-4 inline-flex rounded-full border border-[var(--line)] bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[var(--accent)] hover:bg-[var(--panel)]"
            href="/team"
          >
            Open Team Page
          </Link>
        </WidgetCard>
      </div>
    </div>
  );
}
