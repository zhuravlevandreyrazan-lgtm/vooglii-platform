"use client";

import { FinanceScreen } from "@/features/finance/finance-screen";
import { useFinanceData } from "@/features/finance/hooks/use-finance-data";

export function FinanceLive() {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useFinanceData();

  return (
    <FinanceScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
    />
  );
}
