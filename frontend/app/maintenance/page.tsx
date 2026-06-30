export default function MaintenancePage() {
  return (
    <div className="mx-auto max-w-3xl rounded-[32px] border border-[var(--line)] bg-white/80 p-10 shadow-[var(--shadow-soft)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">Maintenance</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Platform maintenance</h1>
      <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
        This page is reserved for planned maintenance windows and can be linked from future infrastructure or reverse-proxy rules.
      </p>
    </div>
  );
}
