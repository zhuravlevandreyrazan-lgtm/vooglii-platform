import Image from "next/image";

export function EmptyState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-[22px] border border-[var(--line)] bg-[linear-gradient(180deg,#fffdfc_0%,#fbf6ef_100%)] p-5">
      <div className="flex items-center gap-3">
        <Image alt="" className="h-10 w-10 rounded-[14px]" height={40} src="/brand/logo-icon.svg" width={40} />
        <div className="text-sm font-semibold">{title}</div>
      </div>
      <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{description}</p>
    </div>
  );
}
