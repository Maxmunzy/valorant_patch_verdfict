/**
 * 요원 예측을 "공유 가능한 한 줄 문장"으로 압축.
 *
 * 설계 원칙:
 *  1) 가장 강한 정량 신호 1-2개를 앞에 배치 (VCT > 랭크, 상승/하락 추세 포함)
 *  2) 말미에 "{판정} 신호 {확률}" 형태로 훅 마무리 — 캡처/리포스트용
 *  3) 15-30자 내외 목표 — 트위터 카드, 디스코드 임베드에 통째로 들어가는 길이
 *
 * AgentPrediction / AgentDetailData 어느 쪽도 허용 (핵심 필드만 읽음)
 */

interface HeadlineInput {
  agent: string;
  verdict: string;            // nerf_pro, buff_rank, stable, rework ...
  verdict_ko?: string;
  p_nerf: number;
  p_buff: number;
  p_patch: number;
  rank_pr: number;            // %
  rank_wr: number;            // %p deviation from 50
  vct_pr: number;             // %
  vct_current_event?: string | null;
  vct_trend_ratio?: number | null;
  sample_confidence?: "high" | "mid" | "low";
  days_since_patch?: number | null;
  last_direction?: string;
}

// 판정별 한국어 훅 라벨 (공유 문장 말미에 붙음)
const HOOK_LABEL: Record<string, string> = {
  nerf_pro:        "프로 너프 신호",
  nerf_rank:       "랭크 너프 신호",
  nerf_followup:   "추가 너프 가능성",
  correction_nerf: "과버프 보정 너프 신호",
  buff_pro:        "프로 버프 신호",
  buff_rank:       "랭크 버프 신호",
  buff_followup:   "추가 버프 가능성",
  correction_buff: "과너프 보정 버프 신호",
  rework:          "리워크 신호",
  stable:          "안정 평가",
};

/**
 * 주요 확률 (너프/버프 중 큰 쪽 또는 패치 확률) 과 방향을 반환.
 */
function resolveHeadline(a: HeadlineInput): { pct: number; dirHook: string } {
  const v = a.verdict;
  if (v.includes("nerf")) return { pct: a.p_nerf, dirHook: HOOK_LABEL[v] ?? "너프 신호" };
  if (v.includes("buff")) return { pct: a.p_buff, dirHook: HOOK_LABEL[v] ?? "버프 신호" };
  if (v === "rework")    return { pct: a.p_patch, dirHook: HOOK_LABEL[v] };
  // stable: 1 - p_patch (확률은 0-100 퍼센트 스케일로 저장됨)
  return { pct: Math.max(0, 100 - a.p_patch), dirHook: HOOK_LABEL.stable };
}

/**
 * 공유용 한 줄 문장. 문장 끝에 "· {판정 훅} {확률}" 이 붙는다.
 *
 * 예:
 *  "프로 대회 픽률 21.8% · VCT 트렌드 1.6× 상승 · 프로 너프 신호 79"
 *  "랭크 픽률 7.2% · 승률 +4.2%p · 랭크 너프 신호 61"
 */
export function buildShareHeadline(a: HeadlineInput): string {
  const parts: string[] = [];

  // VCT 쪽 신호가 세면 우선 (대회 관심도 훅)
  const hasVct = typeof a.vct_pr === "number" && a.vct_pr >= 5;
  const hasRisingTrend =
    typeof a.vct_trend_ratio === "number" && a.vct_trend_ratio !== null && a.vct_trend_ratio >= 1.3;
  const hasFallingTrend =
    typeof a.vct_trend_ratio === "number" && a.vct_trend_ratio !== null && a.vct_trend_ratio <= 0.7;

  if (hasVct) {
    parts.push(`프로 대회 픽률 ${a.vct_pr.toFixed(1)}%`);
    if (hasRisingTrend) {
      parts.push(`트렌드 ${a.vct_trend_ratio!.toFixed(1)}× 상승`);
    } else if (hasFallingTrend) {
      parts.push(`트렌드 ${a.vct_trend_ratio!.toFixed(1)}× 하락`);
    }
  } else {
    // VCT 약하면 랭크 쪽으로 훅
    if (a.rank_pr >= 3) {
      parts.push(`랭크 픽률 ${a.rank_pr.toFixed(1)}%`);
    } else if (a.rank_pr <= 1) {
      parts.push(`랭크 픽률 ${a.rank_pr.toFixed(1)}% (저조)`);
    }

    // 승률 특이점
    if (a.rank_wr >= 2) {
      parts.push(`승률 +${a.rank_wr.toFixed(1)}%p`);
    } else if (a.rank_wr <= -2) {
      parts.push(`승률 ${a.rank_wr.toFixed(1)}%p`);
    }
  }

  // 최근 패치 조정 후 맥락
  if (a.days_since_patch !== null && a.days_since_patch !== undefined && a.days_since_patch <= 21) {
    if (a.last_direction === "nerf") parts.push("직전 패치 너프 후");
    else if (a.last_direction === "buff") parts.push("직전 패치 버프 후");
  }

  // 너무 빈약하면 역할/샘플 언급
  if (parts.length === 0 && a.sample_confidence === "low") {
    parts.push("표본 부족");
  }

  const { pct, dirHook } = resolveHeadline(a);
  parts.push(`${dirHook} ${Math.round(pct)}`);

  return parts.join(" · ");
}

/**
 * 짧은 2-3단어 축약 — 카드 내부 좁은 공간용.
 */
export function buildShortHook(a: HeadlineInput): string {
  const hasVct = typeof a.vct_pr === "number" && a.vct_pr >= 5;
  const hasRise =
    typeof a.vct_trend_ratio === "number" && a.vct_trend_ratio !== null && a.vct_trend_ratio >= 1.3;

  if (hasVct && hasRise) return `VCT ${a.vct_pr.toFixed(1)}% · 급상승`;
  if (hasVct)            return `VCT ${a.vct_pr.toFixed(1)}%`;
  if (a.rank_pr >= 3)    return `랭크 ${a.rank_pr.toFixed(1)}%`;
  if (a.rank_pr <= 1)    return `저조 ${a.rank_pr.toFixed(1)}%`;
  return "관찰중";
}
