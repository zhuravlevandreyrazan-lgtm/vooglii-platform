import Link from "next/link";
import { ProductDetailField } from "@/features/product-details/components/product-detail-field";
import { HealthBadge, StatusBadge } from "@/shared/status";
import { WidgetCard } from "@/shared/widgets";
import type { ProductDeepLink, ProductOverview } from "@/features/product-details/types";

export function ProductOverviewWidget({
  overview,
  deepLinks,
  loading = false,
  error = null
}: {
  overview: ProductOverview;
  deepLinks: ProductDeepLink[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      error={error}
      loading={loading}
      status={overview.status}
      subtitle={overview.name}
      title="Overview"
    >
      <div className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
          <div className="flex aspect-square items-center justify-center rounded-[28px] border border-dashed border-[var(--line)] bg-[linear-gradient(180deg,#fff8ed_0%,#f6efe2_100%)] p-6 text-center text-sm leading-6 text-[var(--ink-soft)] shadow-[var(--shadow-soft)]">
            {overview.imageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                alt={overview.name}
                className="h-full w-full rounded-[22px] object-cover"
                src={overview.imageUrl}
              />
            ) : (
              <div className="space-y-3">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[20px] bg-white/80 text-2xl font-semibold text-[var(--accent-strong)]">
                  {overview.brand.slice(0, 1)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--ink)]">Preview not available</p>
                  <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
                    Demo-ready fallback artwork keeps the SKU page presentation polished.
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <ProductDetailField label="SKU" value={overview.sku} />
            <ProductDetailField label="Category" value={overview.category} />
            <ProductDetailField label="Brand" value={overview.brand} />
            <ProductDetailField label="Vendor code" value={overview.vendorCode} />
            <ProductDetailField label="ABC" value={overview.abc} />
            <ProductDetailField label="XYZ" value={overview.xyz} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <HealthBadge label={overview.health} score={overview.healthScore ?? undefined} />
          <StatusBadge tone="neutral">{`ABC ${overview.abc}`}</StatusBadge>
          <StatusBadge tone="neutral">{`XYZ ${overview.xyz}`}</StatusBadge>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {deepLinks.map((link) => (
            <Link
              key={link.id}
              className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4 transition hover:-translate-y-0.5 hover:border-[var(--accent)] hover:bg-white"
              href={link.href}
            >
              <p className="text-sm font-semibold">{link.label}</p>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">{link.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </WidgetCard>
  );
}
