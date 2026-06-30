export function ErrorState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-[22px] border border-[color:rgba(184,69,69,0.2)] bg-[color:rgba(184,69,69,0.06)] p-5 text-[var(--danger)]">
      <div className="text-sm font-semibold">{title}</div>
      <p className="mt-2 text-sm leading-6">{description}</p>
    </div>
  );
}
