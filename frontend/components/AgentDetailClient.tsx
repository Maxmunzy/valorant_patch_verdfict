"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import PredBadge from "./PredBadge";
import VctTimeline from "./VctTimeline";
import BackToHome from "./BackToHome";
import { agentPortrait } from "@/lib/agents";
import { SIGNAL_TYPE_ICON } from "@/lib/constants";
import { buildShareHeadline } from "@/lib/headline";

// Extended type for agent detail (includes fields not in the base interface)
export interface VctEventEntry {
  event: string;
  year: number;
  pr: number;
  wr: number;
  picks: number;
  total_maps: number;
  patch_after: string | null;
  act_idx: number;
}

export interface AgentDetailData {
  agent: string;
  act: string;
  role: string;
  rank_pr: number;
  vct_pr: number;
  vct_pr_post?: number;
  vct_pr_current?: number;
  vct_pr_previous?: number;
  vct_current_event?: string | null;
  vct_previous_event?: string | null;
  vct_trend_ratio?: number;
  vct_event_history?: VctEventEntry[];
  rank_wr: number;
  vct_wr: number;
  p_patch: number;
  p_buff: number;
  p_nerf: number;
  p_stable: number;
  acts_since_patch: number;
  last_direction: string;
  vct_act: string | null;
  vct_data_lag: number;
  verdict: string;
  verdict_ko: string;
  verdict_en: string;
  last_patch_version: string | null;
  last_patch_act: string | null;
  last_patch_act_idx?: number | null;
  signals: { type: string; label: string; text: string; tag?: string }[];
  badges?: string[];
  sample_confidence?: "high" | "mid" | "low";
  explanation?: string;
}

const DETAIL_BADGE_COLOR: Record<string, { border: string; fg: string; bg: string }> = {
  "VCT 핵심":     { border: "rgba(239,68,68,0.4)",   fg: "#FCA5A5", bg: "rgba(239,68,68,0.08)" },
  "VCT 주력":     { border: "rgba(239,68,68,0.3)",   fg: "#FCA5A5", bg: "rgba(239,68,68,0.05)" },
  "대회 상승":    { border: "rgba(52,211,153,0.45)", fg: "#6EE7B7", bg: "rgba(52,211,153,0.08)" },
  "너프 MISS":    { border: "rgba(245,158,11,0.4)",  fg: "#FCD34D", bg: "rgba(245,158,11,0.08)" },
  "버프 MISS":    { border: "rgba(245,158,11,0.4)",  fg: "#FCD34D", bg: "rgba(245,158,11,0.08)" },
  "과버프 판정":  { border: "rgba(249,115,22,0.4)",  fg: "#FDBA74", bg: "rgba(249,115,22,0.08)" },
  "과너프 판정":  { border: "rgba(129,140,248,0.4)", fg: "#C7D2FE", bg: "rgba(129,140,248,0.08)" },
  "장기 하락":    { border: "rgba(148,163,184,0.4)", fg: "#CBD5E1", bg: "rgba(148,163,184,0.06)" },
  "고점 요원":    { border: "rgba(167,139,250,0.4)", fg: "#DDD6FE", bg: "rgba(167,139,250,0.06)" },
  "표본 부족":    { border: "rgba(100,116,139,0.4)", fg: "#94A3B8", bg: "rgba(100,116,139,0.08)" },
};
const DETAIL_BADGE_DEFAULT = { border: "rgba(71,85,105,0.4)", fg: "#94A3B8", bg: "rgba(30,41,59,0.3)" };

const CONF_TIER: Record<string, { dot: string; label: string; desc: string }> = {
  high: { dot: "#10B981", label: "HIGH",     desc: "표본 충분 · 최근 데이터" },
  mid:  { dot: "#F59E0B", label: "MID",      desc: "표본 보통 · 수치 참고용" },
  low:  { dot: "#64748B", label: "LOW",      desc: "표본 부족 — 수치 해석 주의" },
};

const VERDICT_COLOR: Record<string, string> = {
  nerf_rank:       "#FF4655",
  nerf_followup:   "#FF4655",
  nerf_pro:        "#FF4655",
  correction_nerf: "#F97316",
  buff_rank:       "#4FC3F7",
  buff_followup:   "#4FC3F7",
  buff_pro:        "#22D3EE",
  correction_buff: "#818CF8",
  rework:          "#A78BFA",
};

const SIGNAL_TAG_COLOR: Record<string, { border: string; dot: string; label: string }> = {
  danger:   { border: "rgba(239,68,68,0.3)",   dot: "#EF4444", label: "#FF4655" },
  warning:  { border: "rgba(245,158,11,0.3)",  dot: "#F59E0B", label: "#FBBF24" },
  positive: { border: "rgba(16,185,129,0.3)",  dot: "#10B981", label: "#34D399" },
  neutral:  { border: "rgba(71,85,105,0.35)",  dot: "#475569", label: "#94A3B8" },
};

// Animated gauge bar
function GaugeBar({
  value,
  color,
  label,
  delay = 0,
}: {
  value: number;
  color: string;
  label: string;
  delay?: number;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span
          className="text-xs uppercase tracking-widest"
          style={{ color: "#94a3b8" }}
        >
          {label}
        </span>
        <span className="text-xs font-num font-bold" style={{ color }}>
          {value.toFixed(0)}%
        </span>
      </div>
      <div className="h-px relative" style={{ background: "rgba(30,41,59,0.8)" }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(value, 100)}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay }}
          className="absolute inset-y-0 left-0"
          style={{ background: color, boxShadow: `0 0 6px ${color}55` }}
        />
      </div>
    </div>
  );
}

// 긴 AI 설명 문단을 문장 단위 근거 블록으로 분해
function ExplanationBlocks({ text, accentColor }: { text: string; accentColor: string }) {
  // 마침표 / 물음표 / 느낌표 뒤에서 분리. 약어 피해를 막기 위해 뒤 공백 강제.
  const raw = text
    .split(/(?<=[.!?。])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

  // 2문장 이하면 굳이 블록 분해 의미 없음 → 원문 그대로
  if (raw.length <= 1) {
    return (
      <p className="text-base leading-relaxed" style={{ color: "#e2e8f0" }}>
        {text}
      </p>
    );
  }

  const [summary, ...reasons] = raw;

  return (
    <div className="space-y-3">
      {/* 요지 */}
      <div
        className="p-3 text-[15px] leading-relaxed font-medium"
        style={{
          background: `${accentColor}08`,
          borderLeft: `2px solid ${accentColor}`,
          color: "#f1f5f9",
        }}
      >
        {summary}
      </div>

      {/* 근거 */}
      {reasons.length > 0 && (
        <ul className="space-y-2">
          {reasons.map((r, i) => (
            <li
              key={i}
              className="flex gap-3 p-2.5 text-sm leading-relaxed"
              style={{ border: "1px solid rgba(30,41,59,0.6)", background: "rgba(8,12,20,0.5)" }}
            >
              <span
                className="shrink-0 text-[10px] font-num font-black w-5 h-5 flex items-center justify-center"
                style={{
                  border: `1px solid ${accentColor}40`,
                  color: accentColor,
                  background: `${accentColor}10`,
                }}
              >
                {i + 1}
              </span>
              <span style={{ color: "#cbd5e1" }}>{r}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Framer Motion variants
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.05 },
  },
};
const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function AgentDetailClient({ data }: { data: AgentDetailData }) {
  const accentColor = VERDICT_COLOR[data.verdict] ?? "#4FC3F7";
  const portrait    = agentPortrait(data.agent);
  const isNerf      = data.verdict.includes("nerf");
  const isBuff      = data.verdict.includes("buff");
  const isRework    = data.verdict === "rework";
  const displayPct  = isNerf ? data.p_nerf : isBuff ? data.p_buff : data.p_patch;
  const dirLabel    = isNerf ? "너프 신호" : isBuff ? "버프 신호" : "패치 확률";

  const patchLabel  = data.last_patch_act
    ? `${data.last_patch_act} · ${data.last_patch_version} 패치 이후`
    : data.last_patch_version
    ? `${data.last_patch_version} 패치 이후`
    : data.act;

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="max-w-2xl mx-auto space-y-3 pt-8"
    >
      {/* Back */}
      <motion.div variants={fadeUp}>
        <BackToHome />
      </motion.div>

      {/* ── HEADER CARD ────────────────────────────────── */}
      <motion.div
        variants={fadeUp}
        className="relative overflow-hidden"
        style={{ border: `1px solid ${accentColor}30`, background: "#0d1220" }}
      >
        {/* Portrait bg — 우측 배치 */}
        {portrait && (
          <div
            className="absolute top-0 bottom-0 right-0 pointer-events-none select-none"
            style={{ width: "55%" }}
          >
            <Image
              src={portrait}
              alt=""
              fill
              className="object-cover opacity-55"
              style={{ objectPosition: "center 22%" }}
              sizes="500px"
            />
            {/* 왼쪽 → 오른쪽 페이드: 카드 내용 영역은 완전 불투명하게 보호 */}
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(to right, rgba(13,18,32,0.95) 0%, rgba(13,18,32,0.45) 35%, rgba(13,18,32,0.1) 75%, transparent 100%)",
              }}
            />
            <div
              className="absolute inset-0"
              style={{ background: "linear-gradient(to top, rgba(13,18,32,0.75) 0%, transparent 40%)" }}
            />
          </div>
        )}

        {/* Top accent line */}
        <div
          className="absolute top-0 left-0 right-0 h-px"
          style={{ background: `linear-gradient(90deg, ${accentColor}, ${accentColor}30, transparent)` }}
        />

        {/* Corner brackets */}
        <div
          className="absolute top-3 left-3 w-3 h-3 pointer-events-none"
          style={{ borderTop: `1px solid ${accentColor}60`, borderLeft: `1px solid ${accentColor}60` }}
        />
        <div
          className="absolute bottom-3 right-3 w-3 h-3 pointer-events-none"
          style={{ borderBottom: `1px solid ${accentColor}40`, borderRight: `1px solid ${accentColor}40` }}
        />

        <div className="relative p-6 space-y-5">
          {/* Agent name + badge */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <div
                className="text-[11px] uppercase tracking-[0.25em] mb-1"
                style={{ color: "#64748b" }}
              >
                AGENT PROFILE // {data.role}
              </div>
              <h1 className="text-4xl font-extrabold text-white tracking-tight leading-none">
                {data.agent}
              </h1>
              <div className="text-xs mt-1" style={{ color: "#94a3b8" }}>
                {patchLabel}
              </div>
              {/* 공유용 한 줄 훅 — 스샷 한 장으로 트위터/디스코드에 붙이면 그대로 콘텐츠 */}
              <div
                className="mt-3 px-3 py-2 text-[13px] sm:text-sm leading-snug font-medium"
                style={{
                  border: `1px solid ${accentColor}40`,
                  background: `linear-gradient(90deg, ${accentColor}15, transparent)`,
                  color: "rgba(240,248,255,0.95)",
                }}
              >
                {buildShareHeadline({
                  agent: data.agent,
                  verdict: data.verdict,
                  verdict_ko: data.verdict_ko,
                  p_nerf: data.p_nerf,
                  p_buff: data.p_buff,
                  p_patch: data.p_patch,
                  rank_pr: data.rank_pr,
                  rank_wr: data.rank_wr,
                  vct_pr: data.vct_pr,
                  vct_current_event: data.vct_current_event,
                  vct_trend_ratio: data.vct_trend_ratio ?? null,
                  sample_confidence: data.sample_confidence,
                  last_direction: data.last_direction,
                })}
              </div>
              {/* 배지: 핵심 신호를 한눈에 */}
              {data.badges && data.badges.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {data.badges.map((b) => {
                    const c = DETAIL_BADGE_COLOR[b] ?? DETAIL_BADGE_DEFAULT;
                    return (
                      <span
                        key={b}
                        className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 whitespace-nowrap"
                        style={{ border: `1px solid ${c.border}`, color: c.fg, background: c.bg }}
                      >
                        {b}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="shrink-0">
              <PredBadge verdict={data.verdict} />
            </div>
          </div>

          {/* Main probability display */}
          <div>
            <div className="flex items-baseline gap-3 mb-1.5">
              <span className="text-6xl font-num font-black tracking-tight leading-none" style={{ color: accentColor }}>
                {displayPct.toFixed(0)}%
              </span>
              <div className="space-y-0.5">
                <div className="text-xs uppercase tracking-widest" style={{ color: "#94a3b8" }}>
                  {dirLabel}
                </div>
                <div className="text-[11px]" style={{ color: "#64748b" }}>
                  전체 패치 확률 {data.p_patch.toFixed(0)}%
                </div>
              </div>
            </div>
            {/* 확률 오해 방지 경고 */}
            <div
              className="mb-3 text-[10px] leading-snug px-2 py-1.5"
              style={{
                color: "rgba(148,163,184,0.7)",
                border: "1px solid rgba(71,85,105,0.4)",
                background: "rgba(13,18,32,0.5)",
              }}
            >
              <span style={{ color: "rgba(148,163,184,0.85)" }}>※</span>{" "}
              실제 확률이 아닌 <span style={{ color: "#cbd5e1", fontWeight: 600 }}>상대적 위험도 점수</span>입니다. 숫자가 높을수록 조정 대상에 가까움.
            </div>

            {/* Probability gauge bars */}
            <div className="space-y-2">
              <GaugeBar value={data.p_nerf} color="#FF4655" label="NERF SIGNAL" delay={0.1} />
              <GaugeBar value={data.p_buff} color="#4FC3F7" label="BUFF SIGNAL" delay={0.2} />
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── AI ANALYSIS (요지 + 근거 블록으로 분해) ─────── */}
      {data.explanation && (
        <motion.div variants={fadeUp}>
          <div
            className="relative p-4"
            style={{ border: `1px solid ${accentColor}20`, background: "#0d1220" }}
          >
            <div
              className="absolute top-0 left-0 right-0 h-px"
              style={{ background: `linear-gradient(90deg, ${accentColor}35, transparent)` }}
            />
            <div className="flex items-center gap-2 mb-3">
              <span
                className="text-[8px] font-black px-1.5 py-px"
                style={{ border: `1px solid ${accentColor}50`, color: accentColor, background: `${accentColor}10` }}
              >
                AI
              </span>
              <span
                className="text-xs uppercase tracking-widest"
                style={{ color: "#94a3b8" }}
              >
                TACTICAL ANALYSIS
              </span>
            </div>

            <ExplanationBlocks text={data.explanation} accentColor={accentColor} />
          </div>
        </motion.div>
      )}

      {/* ── PERFORMANCE DATA ─────────────────────────────── */}
      <motion.div variants={fadeUp} className="space-y-2">
        <div
          className="text-xs uppercase tracking-widest flex items-center gap-2"
          style={{ color: "#64748b" }}
        >
          <div className="w-3 h-px" style={{ background: accentColor }} />
          PERFORMANCE DATA
        </div>

        {/* Rank stats */}
        <div
          className="p-4"
          style={{ border: "1px solid rgba(30,41,59,0.8)", background: "#0d1220" }}
        >
          <div
            className="text-xs uppercase tracking-widest mb-3 flex items-center gap-2"
            style={{ color: "#64748b" }}
          >
            RANKED
            <span style={{ color: "#475569" }}>
              {data.last_patch_version ? `// ${data.last_patch_version} 이후 평균` : "// 패치 이후 평균"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {/* Pick rate */}
            <div>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "#64748b" }}>PICK RATE</div>
              <div
                className="text-2xl font-black"
                style={{ color: data.rank_pr >= 20 ? "#FF4655" : data.rank_pr >= 10 ? "#e2e8f0" : "#64748B" }}
              >
                <span className="font-num">{data.rank_pr.toFixed(1)}%</span>
              </div>
              <div className="text-[11px] mt-0.5" style={{ color: "#64748b" }}>
                {data.rank_pr >= 20 ? "↑ HIGH" : data.rank_pr >= 10 ? "MID" : "↓ LOW"}
              </div>
              <div className="mt-2 h-px" style={{ background: "rgba(30,41,59,0.8)" }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(data.rank_pr * 3, 100)}%` }}
                  transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
                  className="h-full"
                  style={{
                    background: data.rank_pr >= 20 ? "#FF4655" : data.rank_pr >= 10 ? "#94a3b8" : "#334155",
                  }}
                />
              </div>
            </div>
            {/* Win rate */}
            <div>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "#64748b" }}>WIN RATE</div>
              <div
                className="text-2xl font-black"
                style={{ color: data.rank_wr > 2 ? "#FF4655" : data.rank_wr < -2 ? "#4FC3F7" : "#e2e8f0" }}
              >
                <span className="font-num">{(50 + data.rank_wr).toFixed(1)}%</span>
              </div>
              <div className="text-[11px] mt-0.5" style={{ color: "#64748b" }}>
                {data.rank_wr > 2 ? "↑ STRONG" : data.rank_wr < -2 ? "↓ WEAK" : "AVG"}
              </div>
              <div className="mt-2 h-px relative" style={{ background: "rgba(30,41,59,0.8)" }}>
                <div className="absolute inset-y-0 left-1/2 w-px" style={{ background: "rgba(51,65,85,0.8)" }} />
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(Math.abs(data.rank_wr) * 20, 50)}%` }}
                  transition={{ duration: 0.8, delay: 0.45, ease: "easeOut" }}
                  className="absolute inset-y-0"
                  style={{
                    left: data.rank_wr >= 0 ? "50%" : undefined,
                    right: data.rank_wr < 0 ? "50%" : undefined,
                    background: data.rank_wr > 0 ? "#FF4655" : "#4FC3F7",
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* VCT stats */}
        <div
          className="p-4"
          style={{ border: "1px solid rgba(30,41,59,0.8)", background: "#0d1220" }}
        >
          <div
            className="text-xs uppercase tracking-widest mb-3 flex items-center gap-2 flex-wrap"
            style={{ color: "#64748b" }}
          >
            VCT PRO
            {data.vct_current_event ? (
              <>
                <span style={{ color: "#475569" }}>// {data.vct_current_event}</span>
                {data.vct_trend_ratio && data.vct_trend_ratio >= 1.5 && (
                  <span style={{ color: "#6EE7B7" }}>↑ {data.vct_trend_ratio.toFixed(1)}×</span>
                )}
                {data.vct_trend_ratio && data.vct_trend_ratio <= 0.67 && data.vct_pr_previous && data.vct_pr_previous >= 5 && (
                  <span style={{ color: "rgba(252,165,165,0.9)" }}>↓ {data.vct_trend_ratio.toFixed(2)}×</span>
                )}
                {data.vct_data_lag > 2 && (
                  <span style={{ color: "rgba(180,120,0,0.8)" }}>[LAG:{data.vct_data_lag}A]</span>
                )}
              </>
            ) : data.vct_act ? (
              <>
                <span style={{ color: "#475569" }}>
                  {data.last_patch_version ? `// ${data.last_patch_version} 이후 누적` : "// 누적"}
                </span>
                <span style={{ color: "#475569" }}>· UP TO {data.vct_act}</span>
                {data.vct_data_lag > 0 && (
                  <span style={{ color: "rgba(180,120,0,0.8)" }}>[LAG:{data.vct_data_lag}A]</span>
                )}
              </>
            ) : (
              <span style={{ color: "#475569" }}>// NO DATA</span>
            )}
            {/* 신뢰도 tier 뱃지 */}
            {data.sample_confidence && CONF_TIER[data.sample_confidence] && (() => {
              const t = CONF_TIER[data.sample_confidence];
              return (
                <span
                  className="ml-auto inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] tracking-widest"
                  style={{ border: `1px solid ${t.dot}55`, background: `${t.dot}10`, color: t.dot }}
                  title={t.desc}
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: t.dot, boxShadow: `0 0 4px ${t.dot}80` }} />
                  CONF {t.label}
                </span>
              );
            })()}
          </div>
          {/* LOW 신뢰도일 때만 해석 가이드 문구 */}
          {data.sample_confidence === "low" && (
            <div
              className="mb-3 text-[11px] leading-snug px-2 py-1.5"
              style={{
                color: "rgba(148,163,184,0.75)",
                border: "1px solid rgba(100,116,139,0.35)",
                background: "rgba(100,116,139,0.06)",
              }}
            >
              <span style={{ color: "#CBD5E1" }}>표본 부족</span> —
              프로 픽률이 낮거나 데이터가 현재보다 오래된 상태. 숫자 크기보다 {data.last_patch_version ? "패치 이후 추세" : "전반적 방향"}을 먼저 보세요.
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "#64748b" }}>PICK RATE</div>
              <div
                className="text-2xl font-black"
                style={{ color: data.vct_pr >= 30 ? "#FF4655" : data.vct_pr >= 10 ? "#e2e8f0" : "#64748B" }}
              >
                <span className="font-num">{data.vct_pr.toFixed(1)}%</span>
              </div>
              <div className="text-[11px] mt-0.5" style={{ color: "#64748b" }}>
                {data.vct_pr >= 30 ? "META CORE" : data.vct_pr >= 10 ? "ACTIVE" : "NICHE"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "#64748b" }}>WIN RATE</div>
              <div
                className="text-2xl font-black"
                style={{
                  color: data.vct_pr < 5
                    ? "#334155"
                    : data.vct_wr >= 55 ? "#FF4655"
                    : data.vct_wr <= 45 ? "#4FC3F7"
                    : "#e2e8f0",
                }}
              >
                <span className="font-num">{data.vct_pr < 5 ? "—" : `${data.vct_wr.toFixed(1)}%`}</span>
              </div>
              <div className="text-[11px] mt-0.5" style={{ color: "#64748b" }}>
                {data.vct_pr < 5
                  ? "SMALL SAMPLE"
                  : data.vct_wr >= 55 ? "↑ STRONG"
                  : data.vct_wr <= 45 ? "↓ WEAK"
                  : "AVG"}
              </div>
            </div>
          </div>

          {/* ── VCT TIMELINE ─────────────────────────────── */}
          {data.vct_event_history && data.vct_event_history.length >= 2 && (
            <div className="mt-5 pt-4" style={{ borderTop: "1px solid rgba(30,41,59,0.8)" }}>
              <div
                className="text-[10px] uppercase tracking-widest mb-2 flex items-center gap-2"
                style={{ color: "#64748b" }}
              >
                <div className="w-3 h-px" style={{ background: accentColor }} />
                대회별 픽률 추이
                <span style={{ color: "#475569" }}>// LAST {data.vct_event_history.length} EVENTS · 4-REGION 합산</span>
              </div>
              <VctTimeline
                events={data.vct_event_history}
                postAvg={data.vct_pr_post}
                lastPatchActIdx={data.last_patch_act_idx ?? null}
                lastPatchVersion={data.last_patch_version ?? null}
                accentColor={accentColor}
              />
              {/* 누적 대비 비교 힌트 */}
              {data.vct_pr_post !== undefined &&
                data.vct_pr_current !== undefined &&
                Math.abs((data.vct_pr_current ?? 0) - (data.vct_pr_post ?? 0)) >= 3 && (
                  <div className="mt-2 text-[10px]" style={{ color: "rgba(148,163,184,0.75)" }}>
                    <span style={{ color: "rgba(148,163,184,0.6)" }}>※</span>{" "}
                    {data.vct_current_event ?? "현재 대회"} 픽률({(data.vct_pr_current ?? 0).toFixed(1)}%)이
                    {" "}
                    {data.last_patch_version ? `${data.last_patch_version} 이후 누적 평균` : "누적 평균"}({(data.vct_pr_post ?? 0).toFixed(1)}%)
                    {(data.vct_pr_current ?? 0) > (data.vct_pr_post ?? 0) ? "보다 높음 — 상승세" : "보다 낮음 — 하락세"}.
                  </div>
                )}
            </div>
          )}
        </div>
      </motion.div>

      {/* ── SIGNAL ANALYSIS ──────────────────────────────── */}
      {data.signals && data.signals.length > 0 && (
        <motion.div variants={fadeUp} className="space-y-2">
          <div
            className="text-xs uppercase tracking-widest flex items-center gap-2"
            style={{ color: "#64748b" }}
          >
            <div className="w-3 h-px" style={{ background: accentColor }} />
            SIGNAL ANALYSIS
            <span style={{ color: "#475569" }}>// {data.signals.length} FACTORS</span>
          </div>

          {data.signals.map((s, i) => {
            const tc = SIGNAL_TAG_COLOR[s.tag ?? "neutral"] ?? SIGNAL_TAG_COLOR.neutral;
            const typeChar = SIGNAL_TYPE_ICON[s.type] ?? "?";
            return (
              <motion.div
                key={i}
                variants={fadeUp}
                className="relative p-3"
                style={{
                  background: "#0d1220",
                  border: `1px solid ${tc.border}`,
                }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span
                    className="text-[10px] font-bold px-1 py-px shrink-0"
                    style={{
                      border: `1px solid rgba(71,85,105,0.6)`,
                      color: "#94a3b8",
                      background: "rgba(13,18,32,0.8)",
                    }}
                  >
                    {typeChar}
                  </span>
                  <div
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: tc.dot }}
                  />
                  <span className="text-sm font-semibold" style={{ color: tc.label }}>
                    {s.label}
                  </span>
                </div>
                <p
                  className="text-sm leading-relaxed pl-8"
                  style={{ color: "#cbd5e1" }}
                >
                  {s.text}
                </p>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}
