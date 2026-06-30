"use client";

import { useProductDetailsData } from "@/features/product-details/hooks/use-product-details-data";
import { ProductDetailsScreen } from "@/features/product-details/product-details-screen";
import { useWorkspaceContext } from "@/shared/workspace-context";

export function ProductDetailsLive({ sku }: { sku: string }) {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useProductDetailsData(sku);
  const workspace = useWorkspaceContext();

  return (
    <ProductDetailsScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
      workspaceContext={{
        organizationId: workspace.organization?.id ?? null,
        organization: workspace.organization?.name ?? null,
        cabinetId: workspace.cabinet?.id ?? null,
        cabinet: workspace.cabinet?.name ?? null,
        mode: workspace.mode
      }}
    />
  );
}
