"use client";

import { ForecastScreen } from "@/features/forecast/forecast-screen";
import { useForecastData } from "@/features/forecast/hooks/use-forecast-data";

export function ForecastLive() {
  const {
    data,
    loading,
    error,
    reload,
    lastUpdated,
    diagnostics,
    simulation,
    simulationLoading,
    simulateAction
  } = useForecastData();

  return (
    <ForecastScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
      simulation={simulation}
      simulationLoading={simulationLoading}
      simulateAction={simulateAction}
    />
  );
}
