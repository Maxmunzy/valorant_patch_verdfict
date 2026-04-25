export type Locale = "ko" | "en";

interface HeadlineInput {
  agent: string;
  verdict: string;
  verdict_ko?: string;
  p_nerf: number;
  p_buff: number;
  p_patch: number;
  rank_pr: number;
  rank_wr: number;
  vct_pr: number;
  vct_current_event?: string | null;
  vct_trend_ratio?: number | null;
  sample_confidence?: "high" | "mid" | "low";
  days_since_patch?: number | null;
  last_direction?: string;
}

const HOOK_LABEL: Record<Locale, Record<string, string>> = {
  ko: {
    mild_nerf: "너프 신호",
    strong_nerf: "강한 너프 신호",
    mild_buff: "버프 신호",
    strong_buff: "강한 버프 신호",
    rework: "리워크 신호",
    stable: "안정 평가",
  },
  en: {
    mild_nerf: "nerf signal",
    strong_nerf: "strong nerf signal",
    mild_buff: "buff signal",
    strong_buff: "strong buff signal",
    rework: "rework signal",
    stable: "stable",
  },
};

function resolveHeadline(a: HeadlineInput, locale: Locale = "ko"): { pct: number; dirHook: string } {
  const labels = HOOK_LABEL[locale];
  if (a.verdict.includes("nerf")) {
    return { pct: a.p_nerf, dirHook: labels[a.verdict] ?? labels.mild_nerf };
  }
  if (a.verdict.includes("buff")) {
    return { pct: a.p_buff, dirHook: labels[a.verdict] ?? labels.mild_buff };
  }
  if (a.verdict === "rework") {
    return { pct: a.p_patch, dirHook: labels.rework };
  }
  return { pct: Math.max(0, 100 - a.p_patch), dirHook: labels.stable };
}

export function buildShareHeadline(a: HeadlineInput, locale: Locale = "ko"): string {
  const parts: string[] = [];
  const hasVct = typeof a.vct_pr === "number" && a.vct_pr >= 5;
  const rising =
    typeof a.vct_trend_ratio === "number" && a.vct_trend_ratio !== null && a.vct_trend_ratio >= 1.3;
  const falling =
    typeof a.vct_trend_ratio === "number" && a.vct_trend_ratio !== null && a.vct_trend_ratio <= 0.7;

  if (locale === "en") {
    if (hasVct) {
      parts.push(`${a.vct_pr.toFixed(1)}% VCT pick rate`);
      if (rising) parts.push(`${a.vct_trend_ratio!.toFixed(1)}x vs last event`);
      if (falling) parts.push(`${a.vct_trend_ratio!.toFixed(1)}x vs last event`);
    } else {
      parts.push(`${a.rank_pr.toFixed(1)}% rank pick rate`);
      if (a.rank_wr >= 2) parts.push(`win rate +${a.rank_wr.toFixed(1)}pp`);
      if (a.rank_wr <= -2) parts.push(`win rate ${a.rank_wr.toFixed(1)}pp`);
    }
    if (a.days_since_patch !== null && a.days_since_patch !== undefined && a.days_since_patch <= 21) {
      if (a.last_direction === "nerf") parts.push("just nerfed");
      if (a.last_direction === "buff") parts.push("just buffed");
    }
    if (parts.length === 0 && a.sample_confidence === "low") {
      parts.push("low sample");
    }
  } else {
    if (hasVct) {
      parts.push(`VCT 픽률 ${a.vct_pr.toFixed(1)}%`);
      if (rising) parts.push(`최근 대회 대비 ${a.vct_trend_ratio!.toFixed(1)}배 상승`);
      if (falling) parts.push(`최근 대회 대비 ${a.vct_trend_ratio!.toFixed(1)}배 하락`);
    } else {
      parts.push(`랭크 픽률 ${a.rank_pr.toFixed(1)}%`);
      if (a.rank_wr >= 2) parts.push(`승률 +${a.rank_wr.toFixed(1)}%p`);
      if (a.rank_wr <= -2) parts.push(`승률 ${a.rank_wr.toFixed(1)}%p`);
    }
    if (a.days_since_patch !== null && a.days_since_patch !== undefined && a.days_since_patch <= 21) {
      if (a.last_direction === "nerf") parts.push("직전 패치에서 너프됨");
      if (a.last_direction === "buff") parts.push("직전 패치에서 버프됨");
    }
    if (parts.length === 0 && a.sample_confidence === "low") {
      parts.push("표본 적음");
    }
  }

  const { pct, dirHook } = resolveHeadline(a, locale);
  parts.push(`${dirHook} ${Math.round(pct)}%`);

  return parts.join(" · ");
}

export function buildShortHook(a: HeadlineInput): string {
  const hasVct = typeof a.vct_pr === "number" && a.vct_pr >= 5;
  const rising =
    typeof a.vct_trend_ratio === "number" && a.vct_trend_ratio !== null && a.vct_trend_ratio >= 1.3;

  if (hasVct && rising) return `VCT ${a.vct_pr.toFixed(1)}% · 상승세`;
  if (hasVct) return `VCT ${a.vct_pr.toFixed(1)}%`;
  if (a.rank_pr >= 3) return `랭크 ${a.rank_pr.toFixed(1)}%`;
  if (a.rank_pr <= 1) return `비주류 ${a.rank_pr.toFixed(1)}%`;
  return "관찰 중";
}
