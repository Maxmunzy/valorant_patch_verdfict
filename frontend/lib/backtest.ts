/**
 * Walk-forward 백테스트 요약 로더.
 *
 * JSON 은 빌드 시점에 파이썬 (build_backtest_summary.py) 이 생성해서
 * public/backtest-summary.json 으로 배포된다. 서버 컴포넌트에서는 fs 로 직접 읽는다.
 */

import { promises as fs } from "node:fs";
import path from "node:path";

export interface BacktestClassMetric {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface BacktestThreshold {
  threshold: number;
  n: number;
  precision: number;
}

export interface BacktestPerAct {
  act: string;
  act_idx: number;
  n: number;
  hit_dir: number;
  hit_5: number;
}

export interface BacktestLeadHit {
  agent: string;
  predictedAt: string;
  hitAt: string;
  pNerf: number;
  truthAtPred: string;
  truthAtHit: string;
}

export interface BacktestStoryRow {
  agent: string;
  act: string;
  predicted: string;
  truth: string;
  pNerf?: number;
  pBuff?: number;
  kind: "nerf_hit" | "buff_hit" | "nerf_false_positive" | "buff_false_positive";
}

export interface BacktestAgentRow {
  agent: string;
  n: number;
  hits: number;
  misses: number;
  hitRate: number;
}

export interface BacktestPrediction {
  agent: string;
  act: string;
  actIdx: number;
  truth: string;
  predicted: string;
  dirTruth: "stable" | "buff" | "nerf";
  dirPred: "stable" | "buff" | "nerf";
  pStable: number;
  pBuffDir: number;
  pNerfDir: number;
  hitDir: boolean;
  hit5: boolean;
}

export interface BacktestSummary {
  generatedAt: string;
  totalRows: number;
  acts: string[];
  actRange: { first: string | null; last: string | null };
  overall: {
    hitRate3: number;
    hitRate5: number;
    balancedAccuracy: number;
    classes: Record<"stable" | "buff" | "nerf", BacktestClassMetric>;
    confusionMatrix: number[][];
    confusionLabels: string[];
  };
  highConf: {
    nerf: BacktestThreshold[];
    buff: BacktestThreshold[];
  };
  topK: {
    nerfPrecisionTop3PerAct: number;
    nerfTop3Sample: number;
  };
  perAct: BacktestPerAct[];
  stories: {
    leadHits: BacktestLeadHit[];
    bigHits: BacktestStoryRow[];
    bigMisses: BacktestStoryRow[];
  };
  topAgents?: {
    hits: BacktestAgentRow[];
    misses: BacktestAgentRow[];
  };
  predictions: BacktestPrediction[];
}

/**
 * 서버 컴포넌트 전용. public/ 에서 정적 JSON 을 읽어온다.
 * 빌드 시점에 고정되므로 revalidate 는 페이지 레벨에서 관리.
 */
export async function getBacktestSummary(): Promise<BacktestSummary | null> {
  try {
    const filePath = path.join(process.cwd(), "public", "backtest-summary.json");
    const raw = await fs.readFile(filePath, "utf-8");
    return JSON.parse(raw) as BacktestSummary;
  } catch {
    return null;
  }
}
