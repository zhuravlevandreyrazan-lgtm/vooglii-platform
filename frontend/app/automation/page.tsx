import { Suspense } from "react";
import { AutomationLive } from "@/features/automation/automation-live";

export default function AutomationPage() {
  return (
    <Suspense fallback={null}>
      <AutomationLive />
    </Suspense>
  );
}
