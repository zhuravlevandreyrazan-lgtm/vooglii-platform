import { Card } from "@/shared/components/card";

export function ChartPlaceholder({
  title,
  subtitle
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-[var(--ink-soft)]">{subtitle}</p>
        </div>
        <span className="rounded-full bg-[var(--panel-strong)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
          Mock
        </span>
      </div>
      <div className="mt-6 h-52 rounded-[24px] border border-dashed border-[var(--line)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(234,227,214,0.7))] p-5">
        <div className="flex h-full items-end gap-3">
          {["42%", "58%", "33%", "74%", "63%", "80%", "67%"].map((height, index) => (
            <div
              key={`${title}-${index}`}
              className="flex-1 rounded-t-[20px] bg-[linear-gradient(180deg,var(--sky),var(--accent))]"
              style={{ height }}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}
