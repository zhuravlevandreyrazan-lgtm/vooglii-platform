export default function OfflinePage() {
  return (
    <div className="mx-auto max-w-3xl rounded-[32px] border border-[var(--line)] bg-white/80 p-10 shadow-[var(--shadow-soft)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">VOOGLII</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Соединение временно недоступно</h1>
      <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
        Платформа вернётся к работе автоматически, как только восстановится соединение с сетью или инфраструктурой доставки.
      </p>
    </div>
  );
}
