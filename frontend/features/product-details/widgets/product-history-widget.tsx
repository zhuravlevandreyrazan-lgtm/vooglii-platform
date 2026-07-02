import type { ProductHistory } from "@/features/product-details/types";
import { WidgetCard } from "@/shared/widgets";

function formatMoney(value: number | null) {
  return typeof value === "number" ? `₽${value.toLocaleString("ru-RU")}` : "РќРµС‚ РґР°РЅРЅС‹С…";
}

function formatPeriod(period: ProductHistory["period"]) {
  switch (period) {
    case "today":
      return "РЎРµРіРѕРґРЅСЏ";
    case "sevenDays":
      return "7 РґРЅРµР№";
    case "thirtyDays":
      return "30 РґРЅРµР№";
    case "ninetyDays":
      return "90 РґРЅРµР№";
    default:
      return period;
  }
}

export function ProductHistoryWidget({
  history,
  loading = false,
  error = null
}: {
  history: ProductHistory[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard error={error} loading={loading} subtitle="РСЃС‚РѕСЂРёСЏ" title="РџРѕРєР°Р·Р°С‚РµР»Рё РїРѕ РїРµСЂРёРѕРґР°Рј">
      <div className="grid gap-4 lg:grid-cols-2">
        {history.map((item) => (
          <div key={item.period} className="rounded-[22px] border border-[var(--line)] bg-[var(--panel)] p-4">
            <p className="text-sm font-semibold">{formatPeriod(item.period)}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Р’С‹СЂСѓС‡РєР°
                </p>
                <p className="mt-2 text-sm">{formatMoney(item.revenue)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  РџСЂРёР±С‹Р»СЊ
                </p>
                <p className="mt-2 text-sm">{formatMoney(item.profit)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--ink-soft)]">
                  Р—Р°РєР°Р·С‹
                </p>
                <p className="mt-2 text-sm">
                  {typeof item.orders === "number" ? item.orders.toLocaleString("ru-RU") : "РќРµС‚ РґР°РЅРЅС‹С…"}
                </p>
              </div>
            </div>
            <p className="mt-4 text-sm leading-6 text-[var(--ink-soft)]">{item.note}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
