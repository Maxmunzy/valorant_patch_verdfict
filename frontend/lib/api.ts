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
