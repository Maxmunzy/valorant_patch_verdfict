import { API_BASE } from "./constants";

export interface Signal {
  type: string;
  label: string;
  text: string;
  tag?: string;
}

export interface AgentPrediction {
  agent: string;
  act: string;
  role: string;
  rank_pr: number;
  vct_pr: number;
  rank_wr: number;
  vct_wr: number;
  p_patch: number;
  p_buff: number;
  p_nerf: number;
  p_stable: number;
  acts_since_patch: number;
  days_since_patch: number | null;
  last_direction: string;
  vct_act: string | null;
  vct_data_lag: number;
  verdict: string;
  verdict_ko: string;
  verdict_en: string;
  urgency_score: number;
  signals: Signal[];
  badges?: string[];
  sample_confidence?: "high" | "mid" | "low";
  explanation?: string;
}

export async function getAllPredictions(): Promise<AgentPrediction[]> {
  const res = await fetch(`${API_BASE}/predict`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error("Failed to fetch predictions");
  const json = await res.json();
  return json.data as AgentPrediction[];
}

export async function getAgentPrediction(agent: string): Promise<AgentPrediction> {
  const res = await fetch(`${API_BASE}/predict/${encodeURIComponent(agent)}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`Failed to fetch prediction for ${agent}`);
  return res.json() as Promise<AgentPrediction>;
}

// ─── Simulator ──────────────────────────────────────────────────────────────

export interface SkillStat {
  value: number | null;
  unit: string;
  raw: string;
}

export interface SkillSlot {
  name: string;
  name_ko?: string;
  creds?: number;
  charges?: number;
  ult_points?: number;
  stats: Record<string, SkillStat>;
}

export interface AgentMeta {
  role_ko?: string;
}

export type AgentSkillsEntry = Record<string, SkillSlot> & { _meta?: AgentMeta };
export type AgentSkills = Record<string, AgentSkillsEntry>;

export interface SimStatChange {
  agent: string;
  skill: string;
  stat: string;
  old_value: number;
  new_value: number;
}

export interface SimResult {
  changes: {
    agent: string;
    skill: string;
    stat: string;
    old: number;
    new: number;
    direction: string;
    magnitude: string;
  }[];
  impact: {
    agent: string;
    applied_pr_delta: number;
    applied_wr_delta: number;
    pr_range: [number, number, number]; // [p25, median, p75]
    wr_range: [number, number, number];
    confidence: "high" | "medium" | "low";
    n_samples: number;
    similar_cases: {
      patch: string;
      agent: string;
      skill: string;
      change_type: string;
      direction: string;
      description: string;
      match_tier: string;
    }[];
    before: { p_nerf: number; p_buff: number; verdict: string };
    after: { p_nerf: number; p_buff: number; verdict: string };
  }[];
  ripple_effects: {
    agent: string;
    before_verdict: string;
    after_verdict: string;
    before_p_nerf: number;
    after_p_nerf: number;
    before_p_buff: number;
    after_p_buff: number;
  }[];
  before_ranking: { agent: string; p_nerf: number; p_buff: number; p_stable: number; verdict: string }[];
  after_ranking: { agent: string; p_nerf: number; p_buff: number; p_stable: number; verdict: string }[];
}

export async function getAgentSkills(): Promise<AgentSkills> {
  // 스킬 메타는 거의 변하지 않음 → 1시간 revalidate
  const res = await fetch(`${API_BASE}/agent-skills`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error("Failed to fetch agent skills");
  return res.json() as Promise<AgentSkills>;
}

export async function getSimAnalysis(changes: SimStatChange[], resultSummary: string): Promise<string> {
  const res = await fetch(`${API_BASE}/simulate-analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      changes: changes.map((c) => ({
        agent: c.agent,
        skill: c.skill,
        stat: c.stat,
        old_value: c.old_value,
        new_value: c.new_value,
      })),
      result_summary: resultSummary,
    }),
  });
  if (!res.ok) return "AI 분석을 불러올 수 없습니다.";
  const data = await res.json();
  return data.analysis as string;
}

export async function runSimulation(changes: SimStatChange[]): Promise<SimResult> {
  const res = await fetch(`${API_BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ changes }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Simulation failed: ${detail}`);
  }
  return res.json() as Promise<SimResult>;
}
