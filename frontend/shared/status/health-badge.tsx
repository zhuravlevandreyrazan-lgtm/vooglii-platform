import { StatusBadge } from "@/shared/components/status-badge";
import type { StatusTone } from "@/types/platform";

function mapHealthTone(score?: number | null): StatusTone {
  if (typeof score !== "number") {
    return "neutral";
  }
  if (score >= 80) {
    return "healthy";
  }
  if (score >= 60) {
    return "watch";
  }
  return "risk";
}

export function HealthBadge({
  score,
  label
}: {
  score?: number | null;
  label?: string;
}) {
  return (
    <StatusBadge tone={mapHealthTone(score)}>
      {label ?? (typeof score === "number" ? `${score}/100` : "Недостаточно данных")}
    </StatusBadge>
  );
}
