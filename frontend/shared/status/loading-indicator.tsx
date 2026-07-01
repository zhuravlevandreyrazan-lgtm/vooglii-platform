import Image from "next/image";

export function LoadingIndicator({
  label = "Загружаем данные"
}: {
  label?: string;
}) {
  return (
    <div className="inline-flex items-center gap-3 text-sm text-[var(--ink-soft)]" aria-live="polite">
      <Image alt="" className="h-8 w-8 rounded-[12px]" height={32} src="/brand/logo-icon.svg" width={32} />
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[var(--accent)]" />
      <span>{label}</span>
    </div>
  );
}
