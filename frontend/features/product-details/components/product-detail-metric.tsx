export function ProductDetailMetric({
  label,
  value,
  hint
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
        {label}
      </p>
      <p className="mt-3 text-2xl font-semibold tracking-[-0.04em]">{value}</p>
      {hint ? <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{hint}</p> : null}
    </div>
  );
}
