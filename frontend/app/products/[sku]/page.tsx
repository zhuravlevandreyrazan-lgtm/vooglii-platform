import { ProductDetailsLive } from "@/features/product-details/product-details-live";

export default async function ProductDetailsPage({
  params
}: {
  params: Promise<{ sku: string }>;
}) {
  const { sku } = await params;

  return <ProductDetailsLive sku={sku} />;
}
