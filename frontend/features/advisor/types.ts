import type { WorkspaceDiagnostics } from "@/shared/api";
import type { StatusTone } from "@/types/platform";

export type AdvisorModule =
  | "executive"
  | "business"
  | "finance"
  | "advertising"
  | "products"
  | "inventory";

export type AdvisorSource = {
  module: AdvisorModule;
  status: string;
  health: string;
  lastUpdated: string | null;
  source: string;
};

export type AdvisorSummary = {
  businessStatus: string;
  overallHealth: string;
  criticalRisks: number;
  topOpportunities: number;
  recommendationCount: number;
  lastUpdated: string | null;
};

export type AdvisorRecommendation = {
  id: string;
  title: string;
  reason: string;
  priority: "critical" | "high" | "medium" | "low" | "info";
  confidence: string;
  source: AdvisorModule;
  expectedEffect: string;
  status: string;
  href: string;
};

export type AdvisorEvidence = {
  id: string;
  workspace: AdvisorModule;
  source: string;
  reason: string;
  metrics: string[];
  href: string;
};

export type AdvisorRisk = {
  title: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: AdvisorModule;
};

export type AdvisorOpportunity = {
  title: string;
  impact: string;
  source: AdvisorModule;
};

export type AdvisorPriority = {
  label: string;
  value: number;
};

export type AdvisorTimeline = {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  source: AdvisorModule | "advisor";
};

export type AdvisorConversation = {
  placeholder: boolean;
  prompt: string;
  history: Array<{
    id: string;
    role: "user" | "advisor";
    text: string;
  }>;
};

export type AdvisorQueryContext = {
  workspace?: string;
  sku?: string;
  dateFrom?: string;
  dateTo?: string;
  organizationId?: string;
  cabinetId?: string;
};

export type AdvisorQueryRequest = {
  message: string;
  context?: AdvisorQueryContext;
};

export type AdvisorQueryRecommendation = {
  id: string;
  title: string;
  reason: string;
  priority: "critical" | "high" | "medium" | "low" | "info";
  confidence: string;
  href: string;
};

export type AdvisorQueryEvidence = {
  id: string;
  label: string;
  detail: string;
  metrics: string[];
  href: string;
};

export type AdvisorQueryLink = {
  id: string;
  label: string;
  href: string;
  description: string;
};

export type AdvisorQueryRelated = {
  id: string;
  type: "workspace" | "sku" | "campaign" | "report";
  label: string;
  href: string | null;
  note: string | null;
};

export type AdvisorQueryResponse = {
  status: "ok" | "degraded" | "error";
  answer: string;
  summary: string;
  recommendations: AdvisorQueryRecommendation[];
  evidence: AdvisorQueryEvidence[];
  links: AdvisorQueryLink[];
  related: AdvisorQueryRelated[];
  confidence: number;
  diagnostics?: WorkspaceDiagnostics;
};

export type AdvisorConversationStatus = "idle" | "sending" | "ready" | "error";

export type AdvisorQueryMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
  status: AdvisorConversationStatus;
  response?: AdvisorQueryResponse;
};

export type AdvisorQueryState = {
  messages: AdvisorQueryMessage[];
  input: string;
  sending: boolean;
  error: string | null;
  context?: AdvisorQueryContext;
};

export type AdvisorAction = {
  id: string;
  label: string;
  href: string;
};

export type AdvisorInsight = {
  id: string;
  title: string;
  summary: string;
  tone: StatusTone;
};

export type AdvisorSnapshot = {
  summary: AdvisorSummary;
  recommendations: AdvisorRecommendation[];
  evidence: AdvisorEvidence[];
  risks: AdvisorRisk[];
  opportunities: AdvisorOpportunity[];
  priorities: AdvisorPriority[];
  timeline: AdvisorTimeline[];
  actions: AdvisorAction[];
  sources: AdvisorSource[];
  conversation: AdvisorConversation;
  insights: AdvisorInsight[];
  lastUpdated: string | null;
  diagnostics?: WorkspaceDiagnostics;
};
