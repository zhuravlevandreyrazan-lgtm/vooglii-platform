import { formatCurrency, formatPercent } from "@/features/command-center/formatters";
import type { BusinessKpis, BusinessMetric, BusinessSnapshot, BusinessWidget } from "@/features/business/types";
import type { StatusTone } from "@/types/platform";

function toneFromTrend(value: number): StatusTone {
  if (value > 3) {
    return "healthy";
  }
  if (value >= 0) {
    return "accent";
  }
  if (value > -5) {
    return "watch";
  }
  return "risk";
}

function toneFromHealth(score: number): StatusTone {
  if (score >= 80) {
    return "healthy";
  }
  if (score >= 60) {
    return "watch";
  }
  return "risk";
}

function toneFromMargin(margin: number): StatusTone {
  if (margin >= 25) {
    return "healthy";
  }
  if (margin >= 15) {
    return "watch";
  }
  return "risk";
}

function createMetric(
  key: BusinessWidget,
  label: string,
  numericValue: number,
  value: string,
  delta: string,
  note: string,
  tone: StatusTone
): BusinessMetric {
  return {
    key,
    label,
    numericValue,
    value,
    delta,
    note,
    tone,
    state: "ready"
  };
}

export function buildBusinessKpis(snapshot: BusinessSnapshot): BusinessKpis {
  const revenue = snapshot.summary.revenue ?? 0;
  const profit = snapshot.summary.profit ?? 0;
  const margin = snapshot.summary.margin ?? (revenue > 0 ? (profit / revenue) * 100 : 0);
  const orders = snapshot.summary.orders ?? 0;
  const returns = snapshot.summary.returns ?? 0;
  const averageOrderValue = snapshot.summary.averageOrderValue ?? (orders > 0 ? revenue / orders : 0);
  const unitsSold = snapshot.summary.unitsSold ?? 0;
  const healthScore = snapshot.healthScore ?? 0;

  const revenueMetric = createMetric(
    "revenue",
    "Revenue",
    revenue,
    formatCurrency(revenue),
    `${snapshot.trends.revenue >= 0 ? "+" : ""}${snapshot.trends.revenue.toFixed(1)}%`,
    "Gross business revenue for the current operating window.",
    toneFromTrend(snapshot.trends.revenue)
  );

  const profitMetric = createMetric(
    "profit",
    "Profit",
    profit,
    formatCurrency(profit),
    `${snapshot.trends.profit >= 0 ? "+" : ""}${snapshot.trends.profit.toFixed(1)}%`,
    "Profit contribution after current marketplace operating costs.",
    toneFromTrend(snapshot.trends.profit)
  );

  const marginMetric = createMetric(
    "margin",
    "Margin",
    margin,
    formatPercent(margin),
    `${snapshot.trends.margin >= 0 ? "+" : ""}${snapshot.trends.margin.toFixed(1)} pp`,
    "Profit share inside business revenue.",
    toneFromMargin(margin)
  );

  const ordersMetric = createMetric(
    "orders",
    "Orders",
    orders,
    orders.toLocaleString("en-US"),
    `${snapshot.periods.today.orders >= snapshot.periods.yesterday.orders ? "+" : ""}${snapshot.periods.today.orders - snapshot.periods.yesterday.orders} d/d`,
    "Confirmed orders captured in the current period.",
    orders > 0 ? "healthy" : "neutral"
  );

  const returnsMetric = createMetric(
    "returns",
    "Returns",
    returns,
    returns.toLocaleString("en-US"),
    `${snapshot.trends.returns >= 0 ? "+" : ""}${snapshot.trends.returns.toFixed(1)}%`,
    "Units returned or refunded in the same operating window.",
    snapshot.trends.returns > 10 ? "risk" : snapshot.trends.returns > 5 ? "watch" : "neutral"
  );

  const averageOrderValueMetric = createMetric(
    "averageOrderValue",
    "Average Order Value",
    averageOrderValue,
    formatCurrency(averageOrderValue),
    `${snapshot.periods.today.averageOrderValue >= snapshot.periods.yesterday.averageOrderValue ? "+" : ""}${(snapshot.periods.today.averageOrderValue - snapshot.periods.yesterday.averageOrderValue).toFixed(0)} d/d`,
    "Average revenue captured per order.",
    averageOrderValue > 0 ? "accent" : "neutral"
  );

  const unitsSoldMetric = createMetric(
    "unitsSold",
    "Units Sold",
    unitsSold,
    unitsSold.toLocaleString("en-US"),
    `${snapshot.periods.today.unitsSold >= snapshot.periods.yesterday.unitsSold ? "+" : ""}${snapshot.periods.today.unitsSold - snapshot.periods.yesterday.unitsSold} d/d`,
    "Total units sold across the current period.",
    unitsSold > 0 ? "healthy" : "neutral"
  );

  const revenueTrendMetric = createMetric(
    "revenue",
    "Revenue Trend",
    snapshot.trends.revenue,
    `${snapshot.trends.revenue >= 0 ? "+" : ""}${snapshot.trends.revenue.toFixed(1)}%`,
    "vs previous period",
    "Directional trend for revenue.",
    toneFromTrend(snapshot.trends.revenue)
  );

  const profitTrendMetric = createMetric(
    "profit",
    "Profit Trend",
    snapshot.trends.profit,
    `${snapshot.trends.profit >= 0 ? "+" : ""}${snapshot.trends.profit.toFixed(1)}%`,
    "vs previous period",
    "Directional trend for profit.",
    toneFromTrend(snapshot.trends.profit)
  );

  const marginTrendMetric = createMetric(
    "margin",
    "Margin Trend",
    snapshot.trends.margin,
    `${snapshot.trends.margin >= 0 ? "+" : ""}${snapshot.trends.margin.toFixed(1)} pp`,
    "vs previous period",
    "Directional trend for margin.",
    toneFromTrend(snapshot.trends.margin)
  );

  const healthMetric = createMetric(
    "health",
    "Health Score",
    healthScore,
    `${healthScore}/100`,
    snapshot.healthStatus ?? "Unknown",
    "Aggregate operating health for the business workspace.",
    toneFromHealth(healthScore)
  );

  return {
    revenue: revenueMetric,
    profit: profitMetric,
    margin: marginMetric,
    orders: ordersMetric,
    returns: returnsMetric,
    averageOrderValue: averageOrderValueMetric,
    unitsSold: unitsSoldMetric,
    revenueTrend: revenueTrendMetric,
    profitTrend: profitTrendMetric,
    marginTrend: marginTrendMetric,
    healthScore: healthMetric,
    cards: [
      revenueMetric,
      profitMetric,
      marginMetric,
      ordersMetric,
      returnsMetric,
      averageOrderValueMetric,
      unitsSoldMetric,
      healthMetric
    ]
  };
}
