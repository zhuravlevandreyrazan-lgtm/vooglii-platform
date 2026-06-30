"use client";

import { ReportsScreen } from "@/features/reports/reports-screen";
import { useReportsData } from "@/features/reports/hooks/use-reports-data";

export function ReportsLive() {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useReportsData();

  return (
    <ReportsScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
    />
  );
}
