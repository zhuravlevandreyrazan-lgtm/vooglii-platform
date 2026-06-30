export function LoadingIndicator({
  label = "Loading"
}: {
  label?: string;
}) {
  return (
    <div className="inline-flex items-center gap-2 text-sm text-[var(--ink-soft)]" aria-live="polite">
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[var(--accent)]" />
      <span>{label}</span>
    </div>
  );
}
