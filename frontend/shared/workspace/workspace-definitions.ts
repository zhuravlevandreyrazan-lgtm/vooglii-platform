export type WorkspaceDefinition = {
  title: string;
  description: string;
  breadcrumb: string[];
  widgets: Array<{
    title: string;
    subtitle: string;
  }>;
};

export const workspaceDefinitions: Record<string, WorkspaceDefinition> = {
  business: {
    title: "Business",
    description: "Business workspace is the operating lens for revenue momentum, commercial health, and daily performance diagnosis.",
    breadcrumb: ["Platform", "Business"],
    widgets: [
      {
        title: "Revenue Analytics",
        subtitle: "Commercial revenue movement, pacing, and trend interpretation will live here."
      },
      {
        title: "Product KPIs",
        subtitle: "Key SKU and category metrics will be connected to business health and action signals."
      },
      {
        title: "Executive Summary Placeholder",
        subtitle: "Leadership-focused summary cards will appear here as the workspace expands."
      }
    ]
  },
  finance: {
    title: "Finance",
    description: "Finance workspace hosts payout quality, margin interpretation, and confidence-aware financial visibility.",
    breadcrumb: ["Platform", "Finance"],
    widgets: [
      {
        title: "Profit Overview",
        subtitle: "Operational and official profit views will be presented with trust-aware explanations."
      },
      {
        title: "Reconciliation Status",
        subtitle: "Bridges, explainability, and finance status blocks will be available here."
      },
      {
        title: "Finance Actions",
        subtitle: "Rule-based actions for finance review and exception handling will be added here."
      }
    ]
  },
  advertising: {
    title: "Advertising",
    description: "Advertising workspace covers spend control, efficiency diagnostics, and campaign decision support.",
    breadcrumb: ["Platform", "Advertising"],
    widgets: [
      {
        title: "Spend Monitor",
        subtitle: "Budget pacing and spend efficiency widgets will appear in this workspace."
      },
      {
        title: "Campaign Priorities",
        subtitle: "Deterministic campaign review cards and escalation panels will live here."
      },
      {
        title: "Growth Signals",
        subtitle: "ROAS, ACOS, and opportunity-aware growth interpretation will be connected here."
      }
    ]
  },
  products: {
    title: "Products",
    description: "Products workspace focuses on assortment pressure, product readiness, and SKU-level operating actions.",
    breadcrumb: ["Platform", "Products"],
    widgets: [
      {
        title: "SKU Scoreboard",
        subtitle: "Product-level KPIs and category movement widgets will be available here."
      },
      {
        title: "Assortment Watch",
        subtitle: "Pressure points in assortment and lifecycle decisions will surface here."
      },
      {
        title: "Product Actions",
        subtitle: "Operational product recommendations and ownership tracking will be connected here."
      }
    ]
  },
  inventory: {
    title: "Inventory",
    description: "Inventory workspace will manage stock coverage, replenishment timing, and supply stability signals.",
    breadcrumb: ["Platform", "Inventory"],
    widgets: [
      {
        title: "Coverage Radar",
        subtitle: "Stock coverage and days-of-supply widgets will appear in this workspace."
      },
      {
        title: "Replenishment Queue",
        subtitle: "Priority replenishment recommendations and supply coordination will live here."
      },
      {
        title: "Risk Buffer",
        subtitle: "Critical stock gaps and operational buffers will be summarized here."
      }
    ]
  },
  reports: {
    title: "Reports",
    description: "Reports workspace will bundle exports, executive packs, and historical business reporting.",
    breadcrumb: ["Platform", "Reports"],
    widgets: [
      {
        title: "Executive Packs",
        subtitle: "Download-ready leadership reports and summaries will appear here."
      },
      {
        title: "Historical Tables",
        subtitle: "Period comparisons and archived management views will live here."
      },
      {
        title: "Distribution Queue",
        subtitle: "Scheduled report generation and delivery status will be tracked here."
      }
    ]
  },
  advisor: {
    title: "AI Advisor",
    description: "AI Advisor workspace will provide explainable decision support and reviewable advisory flows.",
    breadcrumb: ["Platform", "AI Advisor"],
    widgets: [
      {
        title: "Advice Queue",
        subtitle: "Deterministic and future AI-assisted recommendations will be reviewed here."
      },
      {
        title: "Decision Review",
        subtitle: "Recommendation approval and explanation trails will appear in this workspace."
      },
      {
        title: "Scenario Builder",
        subtitle: "Future what-if and simulation cards will be staged here."
      }
    ]
  },
  settings: {
    title: "Settings",
    description: "Settings workspace contains preferences, integrations, environment controls, and workspace defaults.",
    breadcrumb: ["Platform", "Settings"],
    widgets: [
      {
        title: "Profile Settings",
        subtitle: "User and workspace profile controls will be grouped here."
      },
      {
        title: "Integrations",
        subtitle: "Connected data sources and environment configuration will live here."
      },
      {
        title: "Platform Controls",
        subtitle: "Workspace defaults, feature toggles, and shell options will appear here."
      }
    ]
  }
};
