export default function MaintenancePage() {
  return (
    <div className="mx-auto max-w-3xl rounded-[32px] border border-[var(--line)] bg-white/80 p-10 shadow-[var(--shadow-soft)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">Технические работы</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Платформа временно недоступна</h1>
      <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
        Эта страница используется для плановых технических работ и может включаться через инфраструктуру или прокси-правила.
      </p>
    </div>
  );
}
