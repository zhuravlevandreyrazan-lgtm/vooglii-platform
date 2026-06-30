export function ProductDetailField({
  label,
  value
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
        {label}
      </p>
      <p className="text-sm leading-6 text-[var(--ink)]">{value}</p>
    </div>
  );
}
