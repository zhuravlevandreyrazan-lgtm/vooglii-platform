import { StatusBadge } from "@/shared/components/status-badge";
import type { StatusTone } from "@/types/platform";

function mapSeverityTone(value: string): StatusTone {
  switch (value.toLowerCase()) {
    case "critical":
      return "risk";
    case "high":
      return "watch";
    case "medium":
      return "accent";
    case "low":
      return "neutral";
    default:
      return "healthy";
  }
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <StatusBadge tone={mapSeverityTone(severity)}>{severity}</StatusBadge>;
}
