"use client";

import { InventoryScreen } from "@/features/inventory/inventory-screen";
import { useInventoryData } from "@/features/inventory/hooks/use-inventory-data";

export function InventoryLive() {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useInventoryData();

  return (
    <InventoryScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
    />
  );
}
