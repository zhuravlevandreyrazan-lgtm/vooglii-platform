import { StatusBadge } from "@/shared/components/status-badge";

export function WorkspaceHeader({
  title,
  eyebrow,
  description,
  status
}: {
  title: string;
  eyebrow: string;
  description: string;
  status: string;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-panel)] border border-[var(--line)] bg-white/60 px-6 py-6 shadow-[var(--shadow-soft)] lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--accent-strong)]">
          {eyebrow}
        </p>
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.04em]">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-7 text-[var(--ink-soft)]">
            {description}
          </p>
        </div>
      </div>
      <StatusBadge tone="neutral">{status}</StatusBadge>
    </div>
  );
}
