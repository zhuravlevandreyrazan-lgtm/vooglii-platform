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

function createUnknownMetric(
  key: BusinessWidget,
  label: string,
  note: string,
  delta = "Нет данных за выбранный период"
): BusinessMetric {
  return {
    key,
    label,
    numericValue: 0,
    value: "Нет данных",
    delta,
    note,
    tone: "neutral",
    state: "unknown"
  };
}

export function buildBusinessKpis(snapshot: BusinessSnapshot): BusinessKpis {
  const noData =
    snapshot.healthStatus === "No business data available" ||
    (snapshot.summary.revenue === null &&
      snapshot.summary.profit === null &&
      snapshot.summary.orders === null &&
      snapshot.summary.unitsSold === null);

  if (noData) {
    const revenueMetric = createUnknownMetric("revenue", "Выручка", "За выбранный период данные по выручке пока отсутствуют.");
    const profitMetric = createUnknownMetric("profit", "Прибыль", "Прибыль появится после загрузки продаж и финансовых данных.");
    const marginMetric = createUnknownMetric("margin", "Маржинальность", "Маржинальность рассчитывается после появления выручки и прибыли.");
    const ordersMetric = createUnknownMetric("orders", "Заказы", "Заказы за выбранный период пока недоступны.");
    const returnsMetric = createUnknownMetric("returns", "Возвраты", "Возвраты появятся после загрузки данных о продажах.");
    const averageOrderValueMetric = createUnknownMetric("averageOrderValue", "Средний чек", "Средний чек рассчитывается после появления выручки и заказов.");
    const unitsSoldMetric = createUnknownMetric("unitsSold", "Проданные единицы", "Количество проданных единиц появится после загрузки продаж.");
    const revenueTrendMetric = createUnknownMetric("revenue", "Динамика выручки", "Для динамики нужны заполненные данные как минимум по двум периодам.");
    const profitTrendMetric = createUnknownMetric("profit", "Динамика прибыли", "Для динамики нужны заполненные данные как минимум по двум периодам.");
    const marginTrendMetric = createUnknownMetric("margin", "Динамика маржинальности", "Для динамики нужны заполненные данные как минимум по двум периодам.");
    const healthMetric = {
      ...createUnknownMetric("health", "Здоровье бизнеса", "Оценка состояния бизнеса появится после загрузки агрегатов."),
      delta: snapshot.healthStatus ?? "Нет данных"
    };

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

  const revenue = snapshot.summary.revenue ?? 0;
  const profit = snapshot.summary.profit ?? 0;
  const margin =
    snapshot.summary.margin ??
    (snapshot.summary.revenue !== null && snapshot.summary.profit !== null && revenue > 0 ? (profit / revenue) * 100 : 0);
  const orders = snapshot.summary.orders ?? 0;
  const returns = snapshot.summary.returns ?? 0;
  const averageOrderValue =
    snapshot.summary.averageOrderValue ?? (snapshot.summary.orders !== null && orders > 0 ? revenue / orders : 0);
  const unitsSold = snapshot.summary.unitsSold ?? 0;
  const healthScore = snapshot.healthScore ?? 0;
  const revenueTrend = snapshot.trends.revenue ?? 0;
  const profitTrend = snapshot.trends.profit ?? 0;
  const marginTrend = snapshot.trends.margin ?? 0;
  const returnsTrend = snapshot.trends.returns ?? 0;
  const todayOrders = snapshot.periods.today.orders ?? 0;
  const yesterdayOrders = snapshot.periods.yesterday.orders ?? 0;
  const todayAverageOrderValue = snapshot.periods.today.averageOrderValue ?? 0;
  const yesterdayAverageOrderValue = snapshot.periods.yesterday.averageOrderValue ?? 0;
  const todayUnitsSold = snapshot.periods.today.unitsSold ?? 0;
  const yesterdayUnitsSold = snapshot.periods.yesterday.unitsSold ?? 0;

  const revenueMetric = createMetric(
    "revenue",
    "Выручка",
    revenue,
    formatCurrency(revenue),
    `${revenueTrend >= 0 ? "+" : ""}${revenueTrend.toFixed(1)}%`,
    "Общая выручка бизнеса за выбранный период.",
    toneFromTrend(revenueTrend)
  );

  const profitMetric = createMetric(
    "profit",
    "Прибыль",
    profit,
    formatCurrency(profit),
    `${profitTrend >= 0 ? "+" : ""}${profitTrend.toFixed(1)}%`,
    "Прибыль после текущих расходов маркетплейса.",
    toneFromTrend(profitTrend)
  );

  const marginMetric = createMetric(
    "margin",
    "Маржинальность",
    margin,
    formatPercent(margin),
    `${marginTrend >= 0 ? "+" : ""}${marginTrend.toFixed(1)} pp`,
    "Доля прибыли в выручке бизнеса.",
    toneFromMargin(margin)
  );

  const ordersMetric = createMetric(
    "orders",
    "Заказы",
    orders,
    orders.toLocaleString("en-US"),
    `${todayOrders >= yesterdayOrders ? "+" : ""}${todayOrders - yesterdayOrders} день к дню`,
    "Подтвержденные заказы за выбранный период.",
    orders > 0 ? "healthy" : "neutral"
  );

  const returnsMetric = createMetric(
    "returns",
    "Возвраты",
    returns,
    returns.toLocaleString("en-US"),
    `${returnsTrend >= 0 ? "+" : ""}${returnsTrend.toFixed(1)}%`,
    "Возвраты и отмены за тот же период.",
    returnsTrend > 10 ? "risk" : returnsTrend > 5 ? "watch" : "neutral"
  );

  const averageOrderValueMetric = createMetric(
    "averageOrderValue",
    "Средний чек",
    averageOrderValue,
    formatCurrency(averageOrderValue),
    `${todayAverageOrderValue >= yesterdayAverageOrderValue ? "+" : ""}${(todayAverageOrderValue - yesterdayAverageOrderValue).toFixed(0)} день к дню`,
    "Средняя выручка на один заказ.",
    averageOrderValue > 0 ? "accent" : "neutral"
  );

  const unitsSoldMetric = createMetric(
    "unitsSold",
    "Проданные единицы",
    unitsSold,
    unitsSold.toLocaleString("en-US"),
    `${todayUnitsSold >= yesterdayUnitsSold ? "+" : ""}${todayUnitsSold - yesterdayUnitsSold} день к дню`,
    "Количество проданных единиц за период.",
    unitsSold > 0 ? "healthy" : "neutral"
  );

  const revenueTrendMetric = createMetric(
    "revenue",
    "Динамика выручки",
    revenueTrend,
    `${revenueTrend >= 0 ? "+" : ""}${revenueTrend.toFixed(1)}%`,
    "к предыдущему периоду",
    "Направление изменения выручки.",
    toneFromTrend(revenueTrend)
  );

  const profitTrendMetric = createMetric(
    "profit",
    "Динамика прибыли",
    profitTrend,
    `${profitTrend >= 0 ? "+" : ""}${profitTrend.toFixed(1)}%`,
    "к предыдущему периоду",
    "Направление изменения прибыли.",
    toneFromTrend(profitTrend)
  );

  const marginTrendMetric = createMetric(
    "margin",
    "Динамика маржинальности",
    marginTrend,
    `${marginTrend >= 0 ? "+" : ""}${marginTrend.toFixed(1)} pp`,
    "к предыдущему периоду",
    "Направление изменения маржинальности.",
    toneFromTrend(marginTrend)
  );

  const healthMetric = createMetric(
    "health",
    "Здоровье бизнеса",
    healthScore,
    `${healthScore}/100`,
    snapshot.healthStatus ?? "Нет данных",
    "Сводная оценка состояния бизнес-раздела.",
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
