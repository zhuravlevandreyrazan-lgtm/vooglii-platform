import type { StatusTone } from "@/types/platform";

export type DecisionEngineAction = {
  id: string;
  type: string;
  label: string;
  title: string;
  message: string;
  severity: string;
  priority: string;
  expectedImpact: string;
  confidence: string;
  reason: string;
  action: string;
  source: string;
  tone: StatusTone;
};

export type DecisionEngineChange = {
  id: string;
  type: string;
  title: string;
  message: string;
  severity: string;
  confidence: string;
  source: string;
  tone: StatusTone;
};

export type DecisionEngineEvidence = {
  label: string;
  metric: string;
  value: string;
  source: string;
  confidence: string;
  reason: string;
};

export type DecisionEngineForecast = {
  status: string;
  message: string;
  profit: string;
  profitDirection: string;
  riskLevel: string;
  expectedImpact: string;
  confidence: string;
};

export type DecisionEngineSnapshot = {
  title: string;
  status: string;
  code: string;
  message: string;
  confidence: string;
  tone: StatusTone;
  mainRisk: DecisionEngineAction | null;
  mainOpportunity: DecisionEngineAction | null;
  todayActions: DecisionEngineAction[];
  whatChanged: DecisionEngineChange[];
  forecast: DecisionEngineForecast;
  evidence: DecisionEngineEvidence[];
  sources: string[];
};
