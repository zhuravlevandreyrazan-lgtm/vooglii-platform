import type {
  AdvisorAction,
  AdvisorConversation,
  AdvisorEvidence,
  AdvisorInsight,
  AdvisorOpportunity,
  AdvisorRecommendation,
  AdvisorRisk,
  AdvisorSnapshot,
  AdvisorSource,
  AdvisorSummary,
  AdvisorTimeline
} from "@/features/advisor/types";
import {
  apiEndpoints,
  ApiError,
  assertWorkspacePayload,
  buildWorkspaceDiagnostics,
  createFallbackDiagnostics,
  normalizeRuntimeMetadata,
  requestJson
} from "@/shared/api";

type RawAdvisorSnapshot = {
  summary?: Partial<AdvisorSummary>;
  recommendations?: AdvisorRecommendation[];
  evidence?: AdvisorEvidence[];
  risks?: AdvisorRisk[];
  opportunities?: AdvisorOpportunity[];
  priorities?: AdvisorSnapshot["priorities"];
  timeline?: AdvisorTimeline[];
  actions?: AdvisorAction[];
  sources?: AdvisorSource[];
  conversation?: Partial<AdvisorConversation>;
  insights?: AdvisorInsight[];
  lastUpdated?: string | null;
};

const rawAdvisorSnapshot: RawAdvisorSnapshot = {
  summary: {
    businessStatus: "Attention required",
    overallHealth: "Mixed",
    criticalRisks: 3,
    topOpportunities: 2,
    recommendationCount: 5,
    lastUpdated: "2026-06-30T14:20:00.000Z"
  },
  recommendations: [
    {
      id: "advisor-rec-1",
      title: "Review finance trust before using official profit",
      reason: "Finance workspace still reports degraded quality and low trust for official profit interpretation.",
      priority: "critical",
      confidence: "High",
      source: "finance",
      expectedEffect: "Prevents management decisions from relying on low-confidence finance figures.",
      status: "Open",
      href: "/finance"
    },
    {
      id: "advisor-rec-2",
      title: "Restock the fastest-moving kitchen bundle",
      reason: "Inventory and product workspaces both show a high-risk SKU with low days left.",
      priority: "high",
      confidence: "High",
      source: "inventory",
      expectedEffect: "Protects revenue continuity on a growing product.",
      status: "Open",
      href: "/inventory"
    },
    {
      id: "advisor-rec-3",
      title: "Tune inefficient advertising cluster",
      reason: "Advertising snapshot shows weaker ROAS and duplicate spend pressure on one campaign group.",
      priority: "medium",
      confidence: "Medium",
      source: "advertising",
      expectedEffect: "Recovers campaign efficiency and protects contribution margin.",
      status: "Review",
      href: "/advertising"
    }
  ],
  evidence: [
    {
      id: "advisor-evidence-1",
      workspace: "finance",
      source: "Finance Quality",
      reason: "Official profit remains unconfirmed due to incomplete compatible coverage.",
      metrics: ["Trust 35/100", "Coverage 81%", "Health DEGRADED"],
      href: "/finance"
    },
    {
      id: "advisor-evidence-2",
      workspace: "inventory",
      source: "Restock Plan",
      reason: "Critical replenishment is recommended for a fast-moving SKU.",
      metrics: ["Days Left 5", "Priority Critical", "Warehouse Kazan"],
      href: "/inventory"
    },
    {
      id: "advisor-evidence-3",
      workspace: "advertising",
      source: "Campaign Recommendation",
      reason: "Campaign efficiency weakened while spend stayed elevated.",
      metrics: ["ROAS 3.6x", "ACOS 27.9%", "Duplicate Spend detected"],
      href: "/advertising"
    }
  ],
  risks: [
    {
      title: "Official finance interpretation remains low-confidence",
      severity: "critical",
      source: "finance"
    },
    {
      title: "A top SKU is close to stockout",
      severity: "high",
      source: "inventory"
    },
    {
      title: "Advertising efficiency drift persists",
      severity: "medium",
      source: "advertising"
    }
  ],
  opportunities: [
    {
      title: "Business health still supports selective growth",
      impact: "Expand where margin remains healthy.",
      source: "business"
    },
    {
      title: "One product line can scale with safer stock coverage",
      impact: "Protect revenue while increasing assortment depth.",
      source: "products"
    }
  ],
  priorities: [
    {
      label: "Critical",
      value: 2
    },
    {
      label: "High",
      value: 2
    },
    {
      label: "Medium",
      value: 1
    }
  ],
  timeline: [
    {
      id: "advisor-timeline-1",
      title: "Latest advisor bundle refreshed",
      description: "Cross-workspace recommendation payload was updated.",
      severity: "info",
      source: "advisor"
    },
    {
      id: "advisor-timeline-2",
      title: "Finance caution escalated",
      description: "Official finance confidence remains too low for unguarded management decisions.",
      severity: "high",
      source: "finance"
    },
    {
      id: "advisor-timeline-3",
      title: "Inventory priority updated",
      description: "Restock urgency increased for at least one high-demand SKU.",
      severity: "medium",
      source: "inventory"
    }
  ],
  actions: [
    { id: "advisor-action-1", label: "Open Finance", href: "/finance" },
    { id: "advisor-action-2", label: "Open Products", href: "/products" },
    { id: "advisor-action-3", label: "Open Advertising", href: "/advertising" },
    { id: "advisor-action-4", label: "Open Inventory", href: "/inventory" },
    { id: "advisor-action-5", label: "Open Executive", href: "/executive" }
  ],
  sources: [
    {
      module: "business",
      status: "Active",
      health: "Healthy",
      lastUpdated: "2026-06-30T14:10:00.000Z",
      source: "Business Engine"
    },
    {
      module: "finance",
      status: "Degraded",
      health: "Watch",
      lastUpdated: "2026-06-30T14:12:00.000Z",
      source: "Finance Engine"
    },
    {
      module: "advertising",
      status: "Active",
      health: "Watch",
      lastUpdated: "2026-06-30T14:14:00.000Z",
      source: "Advertising Engine"
    },
    {
      module: "products",
      status: "Active",
      health: "Healthy",
      lastUpdated: "2026-06-30T14:16:00.000Z",
      source: "Product Engine"
    },
    {
      module: "inventory",
      status: "Active",
      health: "Watch",
      lastUpdated: "2026-06-30T14:18:00.000Z",
      source: "Inventory Engine"
    },
    {
      module: "executive",
      status: "Active",
      health: "Healthy",
      lastUpdated: "2026-06-30T14:20:00.000Z",
      source: "Advisor Engine"
    }
  ],
  conversation: {
    placeholder: true,
    prompt: "Ask the advisor about revenue, finance, advertising, products, or inventory once the future AI engine is connected.",
    history: []
  },
  insights: [
    {
      id: "advisor-insight-1",
      title: "Leadership attention should focus on finance trust and stock continuity",
      summary: "The most material cross-workspace issues currently come from low-confidence official finance and a high-priority replenishment need.",
      tone: "watch"
    }
  ],
  lastUpdated: "2026-06-30T14:20:00.000Z"
};

export function normalizeAdvisorSnapshot(
  raw: RawAdvisorSnapshot,
  diagnostics = createFallbackDiagnostics()
): AdvisorSnapshot {
  return {
    summary: {
      businessStatus: raw.summary?.businessStatus ?? "Unknown",
      overallHealth: raw.summary?.overallHealth ?? "Unknown",
      criticalRisks: raw.summary?.criticalRisks ?? 0,
      topOpportunities: raw.summary?.topOpportunities ?? 0,
      recommendationCount: raw.summary?.recommendationCount ?? 0,
      lastUpdated: raw.summary?.lastUpdated ?? raw.lastUpdated ?? null
    },
    recommendations: raw.recommendations ?? [],
    evidence: raw.evidence ?? [],
    risks: raw.risks ?? [],
    opportunities: raw.opportunities ?? [],
    priorities: raw.priorities ?? [],
    timeline: raw.timeline ?? [],
    actions: raw.actions ?? [],
    sources: raw.sources ?? [],
    conversation: {
      placeholder: raw.conversation?.placeholder ?? false,
      prompt:
        raw.conversation?.prompt ??
        "Спросите советника о финансах, рекламе, товарах, остатках или общей динамике бизнеса.",
      history: raw.conversation?.history ?? []
    },
    insights: raw.insights ?? [],
    lastUpdated: raw.lastUpdated ?? null,
    diagnostics
  };
}

export function getAdvisorMockSnapshot() {
  return normalizeAdvisorSnapshot(rawAdvisorSnapshot);
}

function isRawAdvisorSnapshot(value: unknown): value is RawAdvisorSnapshot {
  return typeof value === "object" && value !== null;
}

export async function fetchAdvisorSnapshot(signal?: AbortSignal) {
  const payload = await requestJson<unknown>(apiEndpoints.advisor, { signal });
  const record = assertWorkspacePayload(payload, apiEndpoints.advisor, "Advisor");

  if (!isRawAdvisorSnapshot(record)) {
    throw new ApiError("Advisor API payload has an invalid shape.", {
      code: "invalid_shape",
      status: null,
      url: apiEndpoints.advisor
    });
  }

  const runtime = normalizeRuntimeMetadata(record);
  return normalizeAdvisorSnapshot(
    record,
    buildWorkspaceDiagnostics({ runtime, validationStatus: "ok" })
  );
}
