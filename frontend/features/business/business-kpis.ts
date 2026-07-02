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

function formatSigned(value: number, suffix = "%"): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
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

  const revenue = snapshot.summary.revenue;
  const profit = snapshot.summary.profit;
  const margin =
    snapshot.summary.margin ??
    (snapshot.summary.revenue !== null && snapshot.summary.profit !== null && snapshot.summary.revenue > 0
      ? (snapshot.summary.profit / snapshot.summary.revenue) * 100
      : null);
  const orders = snapshot.summary.orders;
  const returns = snapshot.summary.returns;
  const averageOrderValue =
    snapshot.summary.averageOrderValue ??
    (snapshot.summary.orders !== null &&
    snapshot.summary.orders > 0 &&
    snapshot.summary.revenue !== null
      ? snapshot.summary.revenue / snapshot.summary.orders
      : null);
  const unitsSold = snapshot.summary.unitsSold;
  const healthScore = snapshot.healthScore ?? null;
  const revenueTrend = snapshot.trends.revenue;
  const profitTrend = snapshot.trends.profit;
  const marginTrend = snapshot.trends.margin;
  const returnsTrend = snapshot.trends.returns;
  const todayOrders = snapshot.periods.today.orders;
  const yesterdayOrders = snapshot.periods.yesterday.orders;
  const todayAverageOrderValue = snapshot.periods.today.averageOrderValue;
  const yesterdayAverageOrderValue = snapshot.periods.yesterday.averageOrderValue;
  const todayUnitsSold = snapshot.periods.today.unitsSold;
  const yesterdayUnitsSold = snapshot.periods.yesterday.unitsSold;

  const revenueMetric =
    revenue !== null && revenueTrend !== null
      ? createMetric(
          "revenue",
          "Выручка",
          revenue,
          formatCurrency(revenue),
          formatSigned(revenueTrend),
          "Общая выручка бизнеса за выбранный период.",
          toneFromTrend(revenueTrend)
        )
      : createUnknownMetric("revenue", "Выручка", "Данных по выручке за выбранный период пока нет.");

  const profitMetric =
    profit !== null && profitTrend !== null
      ? createMetric(
          "profit",
          "Прибыль",
          profit,
          formatCurrency(profit),
          formatSigned(profitTrend),
          "Прибыль после текущих расходов маркетплейса.",
          toneFromTrend(profitTrend)
        )
      : createUnknownMetric("profit", "Прибыль", "Прибыль появится после загрузки финансовых и продажных данных.");

  const marginMetric =
    margin !== null && marginTrend !== null
      ? createMetric(
          "margin",
          "Маржинальность",
          margin,
          formatPercent(margin),
          formatSigned(marginTrend, " pp"),
          "Доля прибыли в выручке бизнеса.",
          toneFromMargin(margin)
        )
      : createUnknownMetric("margin", "Маржинальность", "Маржинальность появится, когда будут доступны выручка и прибыль.");

  const ordersMetric =
    orders !== null && todayOrders !== null && yesterdayOrders !== null
      ? createMetric(
          "orders",
          "Заказы",
          orders,
          orders.toLocaleString("en-US"),
          `${todayOrders >= yesterdayOrders ? "+" : ""}${todayOrders - yesterdayOrders} день к дню`,
          "Подтвержденные заказы за выбранный период.",
          orders > 0 ? "healthy" : "neutral"
        )
      : createUnknownMetric("orders", "Заказы", "Заказы за выбранный период пока недоступны.");

  const returnsMetric =
    returns !== null && returnsTrend !== null
      ? createMetric(
          "returns",
          "Возвраты",
          returns,
          returns.toLocaleString("en-US"),
          formatSigned(returnsTrend),
          "Возвраты и отмены за тот же период.",
          returnsTrend > 10 ? "risk" : returnsTrend > 5 ? "watch" : "neutral"
        )
      : createUnknownMetric("returns", "Возвраты", "Данные по возвратам появятся после синхронизации.");

  const averageOrderValueMetric =
    averageOrderValue !== null && todayAverageOrderValue !== null && yesterdayAverageOrderValue !== null
      ? createMetric(
          "averageOrderValue",
          "Средний чек",
          averageOrderValue,
          formatCurrency(averageOrderValue),
          `${todayAverageOrderValue >= yesterdayAverageOrderValue ? "+" : ""}${(todayAverageOrderValue - yesterdayAverageOrderValue).toFixed(0)} день к дню`,
          "Средняя выручка на один заказ.",
          averageOrderValue > 0 ? "accent" : "neutral"
        )
      : createUnknownMetric("averageOrderValue", "Средний чек", "Средний чек станет доступен, когда появятся выручка и заказы.");

  const unitsSoldMetric =
    unitsSold !== null && todayUnitsSold !== null && yesterdayUnitsSold !== null
      ? createMetric(
          "unitsSold",
          "Проданные единицы",
          unitsSold,
          unitsSold.toLocaleString("en-US"),
          `${todayUnitsSold >= yesterdayUnitsSold ? "+" : ""}${todayUnitsSold - yesterdayUnitsSold} день к дню`,
          "Количество проданных единиц за период.",
          unitsSold > 0 ? "healthy" : "neutral"
        )
      : createUnknownMetric("unitsSold", "Проданные единицы", "Количество проданных единиц появится после загрузки продаж.");

  const revenueTrendMetric =
    revenueTrend !== null
      ? createMetric(
          "revenue",
          "Динамика выручки",
          revenueTrend,
          formatSigned(revenueTrend),
          "к предыдущему периоду",
          "Направление изменения выручки.",
          toneFromTrend(revenueTrend)
        )
      : createUnknownMetric("revenue", "Динамика выручки", "Для динамики нужны данные как минимум за два равноценных периода.");

  const profitTrendMetric =
    profitTrend !== null
      ? createMetric(
          "profit",
          "Динамика прибыли",
          profitTrend,
          formatSigned(profitTrend),
          "к предыдущему периоду",
          "Направление изменения прибыли.",
          toneFromTrend(profitTrend)
        )
      : createUnknownMetric("profit", "Динамика прибыли", "Данных для динамики прибыли пока недостаточно.");

  const marginTrendMetric =
    marginTrend !== null
      ? createMetric(
          "margin",
          "Динамика маржинальности",
          marginTrend,
          formatSigned(marginTrend, " pp"),
          "к предыдущему периоду",
          "Направление изменения маржинальности.",
          toneFromTrend(marginTrend)
        )
      : createUnknownMetric("margin", "Динамика маржинальности", "Данных для динамики маржинальности пока недостаточно.");

  const healthMetric =
    healthScore !== null
      ? createMetric(
          "health",
          "Здоровье бизнеса",
          healthScore,
          `${healthScore}/100`,
          snapshot.healthStatus ?? "Нет данных",
          "Сводная оценка состояния бизнес-раздела.",
          toneFromHealth(healthScore)
        )
      : {
          ...createUnknownMetric("health", "Здоровье бизнеса", "Оценка состояния появится после загрузки бизнес-агрегатов."),
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
