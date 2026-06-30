"use client";

import { AdvertisingScreen } from "@/features/advertising/advertising-screen";
import { useAdvertisingData } from "@/features/advertising/hooks/use-advertising-data";

export function AdvertisingLive() {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useAdvertisingData();

  return (
    <AdvertisingScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
    />
  );
}
