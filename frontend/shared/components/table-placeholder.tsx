import { Card } from "@/shared/components/card";

export function TablePlaceholder({
  title,
  columns
}: {
  title: string;
  columns: string[];
}) {
  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
          Placeholder
        </span>
      </div>
      <div className="mt-5 overflow-hidden rounded-[20px] border border-[var(--line)]">
        <div className="grid bg-[var(--panel-strong)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">
          <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}>
            {columns.map((column) => (
              <span key={column}>{column}</span>
            ))}
          </div>
        </div>
        <div className="space-y-2 p-4">
          {[0, 1, 2, 3].map((row) => (
            <div
              key={`${title}-row-${row}`}
              className={`grid gap-3 rounded-2xl bg-white/70 px-3 py-3`}
              style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}
            >
              {columns.map((column) => (
                <div key={`${column}-${row}`} className="h-3 rounded-full bg-[var(--background-strong)]" />
              ))}
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
