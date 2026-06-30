export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-3xl rounded-[32px] border border-[var(--line)] bg-white/80 p-10 shadow-[var(--shadow-soft)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">404</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Page not found</h1>
      <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
        The requested route is unavailable or has not been prepared for the current release candidate environment.
      </p>
    </div>
  );
}
