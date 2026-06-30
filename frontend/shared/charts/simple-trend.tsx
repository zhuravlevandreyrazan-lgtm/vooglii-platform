type SimpleTrendPoint = {
  label: string;
  value: number;
};

function buildPolyline(points: SimpleTrendPoint[], width: number, height: number) {
  const values = points.map((point) => point.value);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  return points
    .map((point, index) => {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
      const y = height - ((point.value - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");
}

export function SimpleTrend({
  points,
  className = ""
}: {
  points: SimpleTrendPoint[];
  className?: string;
}) {
  const filtered = points.filter((point) => Number.isFinite(point.value));
  if (filtered.length < 2) {
    return null;
  }

  const polyline = buildPolyline(filtered, 220, 64);
  const area = `${polyline} 220,64 0,64`;

  return (
    <div className={`rounded-[20px] border border-[var(--line)] bg-white/80 p-3 ${className}`.trim()}>
      <svg aria-hidden="true" className="h-20 w-full" preserveAspectRatio="none" viewBox="0 0 220 64">
        <defs>
          <linearGradient id="trend-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(208,104,63,0.28)" />
            <stop offset="100%" stopColor="rgba(208,104,63,0.03)" />
          </linearGradient>
        </defs>
        <polygon fill="url(#trend-fill)" points={area} />
        <polyline
          fill="none"
          points={polyline}
          stroke="var(--accent-strong)"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.5"
        />
      </svg>
      <div className="mt-2 grid grid-cols-4 gap-2">
        {filtered.map((point) => (
          <div key={point.label} className="min-w-0">
            <p className="truncate text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
              {point.label}
            </p>
            <p className="mt-1 text-xs font-semibold text-[var(--ink)]">
              {Math.round(point.value).toLocaleString("en-US")}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
