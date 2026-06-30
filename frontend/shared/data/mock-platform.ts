import type { CommandCenterSnapshot, NavItem } from "@/types/platform";

export const primaryNavigation: NavItem[] = [
  {
    key: "command-center",
    label: "Command Center",
    href: "/",
    description: "Executive view, health, priorities, and cross-workspace routing."
  },
  {
    key: "business",
    label: "Business",
    href: "/business",
    description: "Operating condition, trend diagnostics, and action signals."
  },
  {
    key: "finance",
    label: "Finance",
    href: "/finance",
    description: "Payout clarity, margin discipline, and trusted financial status."
  },
  {
    key: "products",
    label: "Products",
    href: "/products",
    description: "SKU pressure, assortment movement, and stock-aware actions."
  },
  {
    key: "advertising",
    label: "Advertising",
    href: "/advertising",
    description: "Spend efficiency, risk control, and campaign direction."
  },
  {
    key: "analytics",
    label: "Analytics",
    href: "/analytics",
    description: "Evidence trails, comparisons, and deeper business context."
  },
  {
    key: "ai",
    label: "AI",
    href: "/ai",
    description: "Copilot, decision support, and explainable intelligence."
  },
  {
    key: "system",
    label: "System",
    href: "/system",
    description: "Source status, sync readiness, and platform diagnostics."
  },
  {
    key: "settings",
    label: "Settings",
    href: "/settings",
    description: "Account, integrations, and workspace preferences."
  }
];

export const commandCenterMock: CommandCenterSnapshot = {
  businessHealth: {
    score: 84,
    status: "Stable Growth",
    summary:
      "Revenue momentum is holding, but margin pressure and one stock gap need attention before they turn into avoidable loss."
  },
  executiveBrief: {
    id: "brief-1",
    eyebrow: "Executive Brief",
    title: "Protect margin today and clear the upcoming stock gap in top assortment.",
    summary:
      "The platform sees healthy sales velocity, but two signals stand out: ad spend is growing faster than contribution margin, and one core SKU cluster may hit a stock squeeze within five days.",
    confidence: "High confidence",
    sources: ["Sales trend", "Stock coverage", "Ad efficiency"],
    tone: "accent"
  },
  kpis: [
    {
      label: "Business Health",
      value: "84/100",
      delta: "+4 vs last week",
      tone: "healthy",
      note: "Strong sales with manageable pressure."
    },
    {
      label: "Net Margin",
      value: "22.4%",
      delta: "-1.8 pp",
      tone: "watch",
      note: "Acquisition costs are rising faster than payout quality."
    },
    {
      label: "Forecast Target",
      value: "93%",
      delta: "+7 pp",
      tone: "healthy",
      note: "Current pace is close to monthly plan."
    },
    {
      label: "Stock Risk",
      value: "3 SKUs",
      delta: "1 critical",
      tone: "risk",
      note: "Action window remains open this week."
    }
  ],
  timeline: [
    {
      id: "tm-1",
      time: "08:10",
      title: "Business health recalculated",
      detail: "Sales and stock signals improved, but finance pressure remained unchanged.",
      tone: "neutral"
    },
    {
      id: "tm-2",
      time: "10:30",
      title: "Ad efficiency cooled",
      detail: "Spend accelerated faster than profit contribution on one campaign cluster.",
      tone: "watch"
    },
    {
      id: "tm-3",
      time: "13:45",
      title: "Top assortment stock risk detected",
      detail: "Coverage on one high-volume SKU family dropped below the preferred threshold.",
      tone: "risk"
    }
  ],
  actions: [
    {
      id: "ac-1",
      title: "Review campaign group with widening CAC",
      owner: "Advertising Lead",
      eta: "Today",
      tone: "watch"
    },
    {
      id: "ac-2",
      title: "Prepare replenishment plan for core summer SKU block",
      owner: "Operations",
      eta: "Next 24h",
      tone: "risk"
    },
    {
      id: "ac-3",
      title: "Validate margin movement in Finance workspace",
      owner: "Finance",
      eta: "This afternoon",
      tone: "accent"
    }
  ],
  alerts: [
    {
      id: "al-1",
      title: "Critical SKU coverage below preferred floor",
      detail: "A top revenue cluster can slip into stockout pressure within five days if replenishment is not confirmed.",
      tone: "risk"
    },
    {
      id: "al-2",
      title: "Ad spend growth outpacing contribution margin",
      detail: "Efficiency remains acceptable, but the trend needs intervention before profit compression becomes structural.",
      tone: "watch"
    }
  ],
  workspaces: [
    {
      title: "Business",
      href: "/business",
      summary: "See business health drivers, trend turns, and operating pressure.",
      status: "Ready"
    },
    {
      title: "Finance",
      href: "/finance",
      summary: "Inspect payout quality, margin movement, and source confidence.",
      status: "Ready"
    },
    {
      title: "Products",
      href: "/products",
      summary: "Track SKU pressure, assortment performance, and stock signals.",
      status: "Ready"
    },
    {
      title: "Advertising",
      href: "/advertising",
      summary: "Review spend control, efficiency drift, and campaign priorities.",
      status: "Ready"
    }
  ],
  notifications: [
    {
      id: "nt-1",
      title: "Mock mode active",
      description: "The frontend uses an isolated mock data layer and is ready for backend integration later.",
      tone: "accent"
    },
    {
      id: "nt-2",
      title: "Source confidence placeholder",
      description: "Command Center can already display data trust and degraded states.",
      tone: "neutral"
    }
  ]
};
