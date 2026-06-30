"use client";

import { ProductsScreen } from "@/features/products/products-screen";
import { useProductsData } from "@/features/products/hooks/use-products-data";

export function ProductsLive() {
  const { data, loading, error, reload, lastUpdated, diagnostics } = useProductsData();

  return (
    <ProductsScreen
      data={data}
      diagnostics={diagnostics}
      error={error}
      lastUpdated={lastUpdated}
      loading={loading}
      reload={reload}
    />
  );
}
