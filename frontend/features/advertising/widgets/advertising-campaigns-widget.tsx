import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import { StatusBadge } from "@/shared/status";
import { localizeStatus } from "@/shared/ui/status-labels";
import { WidgetCard } from "@/shared/widgets";
import type { AdvertisingCampaign } from "@/features/advertising/types";

function toneForStatus(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes("await")) {
    return "neutral" as const;
  }
  if (normalized.includes("need")) {
    return "watch" as const;
  }
  if (normalized.includes("scal")) {
    return "accent" as const;
  }
  return "healthy" as const;
}

export function AdvertisingCampaignsWidget({
  campaigns,
  loading = false,
  error = null
}: {
  campaigns: AdvertisingCampaign[];
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <WidgetCard
      empty={campaigns.length === 0}
      emptyMessage="Таблица кампаний появится здесь, когда backend начнет отдавать построчные данные по рекламе."
      error={error}
      loading={loading}
      subtitle="Таблица кампаний"
      title="Кампании"
    >
      <div className="space-y-3">
        {campaigns.map((campaign) => (
          <div key={campaign.id} className="rounded-[22px] border border-[var(--line)] bg-white/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold">{campaign.campaign}</div>
                <div className="mt-1 text-sm text-[var(--ink-soft)]">{campaign.recommendation}</div>
              </div>
              <StatusBadge tone={toneForStatus(campaign.status)}>{localizeStatus(campaign.status)}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Расход</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(campaign.spend)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Выручка</div>
                <div className="mt-1 text-sm font-semibold">{formatCurrency(campaign.revenue)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ROAS</div>
                <div className="mt-1 text-sm font-semibold">{campaign.roas === null ? "Нет данных" : `${campaign.roas.toFixed(1)}x`}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">ACOS</div>
                <div className="mt-1 text-sm font-semibold">{campaign.acos === null ? "Нет данных" : formatPercent(campaign.acos)}</div>
              </div>
              <div className="md:col-span-2">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--ink-soft)]">Рекомендация</div>
                <div className="mt-1 text-sm font-semibold">{campaign.recommendation}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
