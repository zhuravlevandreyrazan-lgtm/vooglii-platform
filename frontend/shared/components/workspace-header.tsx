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
    <div className="flex flex-col gap-4 rounded-[28px] border border-[var(--line)] bg-[linear-gradient(180deg,rgba(255,253,252,0.88)_0%,rgba(251,246,239,0.9)_100%)] px-5 py-5 shadow-[var(--shadow-soft)] lg:flex-row lg:items-end lg:justify-between">
      <div className="space-y-2.5">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--accent-strong)]">
          {eyebrow}
        </p>
        <div>
          <h1 className="text-[2rem] font-semibold tracking-[-0.045em]">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--ink-soft)]">
            {description}
          </p>
        </div>
      </div>
      <StatusBadge tone="neutral">{status}</StatusBadge>
    </div>
  );
}
