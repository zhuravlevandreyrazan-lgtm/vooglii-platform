import { StatusBadge } from "@/shared/status";

export type PageHeaderProps = {
  title: string;
  subtitle: string;
  breadcrumb: string[];
  updatedAt?: string;
  actions?: React.ReactNode;
};

export function PageHeader({
  title,
  subtitle,
  breadcrumb,
  updatedAt,
  actions
}: PageHeaderProps) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-[var(--line)] bg-white/70 px-6 py-6 shadow-[var(--shadow-soft)]">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
            {breadcrumb.map((item, index) => (
              <span key={`${item}-${index}`} className="inline-flex items-center gap-2">
                {index > 0 ? <span className="text-[var(--line)]">/</span> : null}
                <span>{item}</span>
              </span>
            ))}
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-[-0.04em]">{title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-[var(--ink-soft)]">{subtitle}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {updatedAt ? <StatusBadge tone="neutral">Updated {updatedAt}</StatusBadge> : null}
          {actions}
        </div>
      </div>
    </div>
  );
}
