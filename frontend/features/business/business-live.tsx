"use client";

import { BusinessScreen } from "@/features/business/business-screen";
import { useBusinessData } from "@/features/business/hooks/use-business-data";

export function BusinessLive() {
  const { data, kpis, insight, alerts, loading, error, reload, lastUpdated, diagnostics } = useBusinessData();

  return (
    <BusinessScreen
      alerts={alerts}
      data={data}
      diagnostics={diagnostics}
      error={error}
      insight={insight}
      kpis={kpis}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
    />
  );
}
