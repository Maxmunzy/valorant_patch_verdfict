"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import PredBadge from "./PredBadge";
import { agentPortrait } from "@/lib/agents";
import { SIGNAL_TYPE_ICON } from "@/lib/constants";

// Extended type for agent detail (includes fields not in the base interface)
export interface AgentDetailData {
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
  last_direction: string;
  vct_act: string | null;
  vct_data_lag: number;
  verdict: string;
  verdict_ko: string;
  verdict_en: string;
  last_patch_version: string | null;
  last_patch_act: string | null;
  signals: { type: string; label: string; text: string; tag?: string }[];
  explanation?: string;
}

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
        <span className="text-xs font-bold" style={{ color }}>
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
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs uppercase tracking-widest transition-colors"
          style={{ color: "#64748b" }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "#e2e8f0")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "#64748b")}
        >
          ← BACK TO OVERVIEW
        </Link>
      </motion.div>

      {/* ── HEADER CARD ────────────────────────────────── */}
      <motion.div
        variants={fadeUp}
        className="relative overflow-hidden"
        style={{ border: `1px solid ${accentColor}30`, background: "#0d1220" }}
      >
        {/* Portrait bg */}
        {portrait && (
          <div className="absolute inset-0 pointer-events-none select-none">
            <Image
              src={portrait}
              alt=""
              fill
              className="object-cover object-top opacity-10"
              sizes="672px"
            />
            <div
              className="absolute inset-0"
              style={{ background: "linear-gradient(to right, #0d1220 50%, #0d122070 80%, transparent)" }}
            />
            <div
              className="absolute inset-0"
              style={{ background: "linear-gradient(to top, #0d1220 30%, transparent)" }}
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
              <h1 className="text-4xl font-black text-white tracking-tight leading-none">
                {data.agent}
              </h1>
              <div className="text-xs mt-1" style={{ color: "#94a3b8" }}>
                {patchLabel}
              </div>
            </div>
            <div className="shrink-0">
              <PredBadge verdict={data.verdict} />
            </div>
          </div>

          {/* Main probability display */}
          <div>
            <div className="flex items-baseline gap-3 mb-3">
              <span className="text-6xl font-black leading-none" style={{ color: accentColor }}>
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

            {/* Probability gauge bars */}
            <div className="space-y-2">
              <GaugeBar value={data.p_nerf} color="#FF4655" label="NERF SIGNAL" delay={0.1} />
              <GaugeBar value={data.p_buff} color="#4FC3F7" label="BUFF SIGNAL" delay={0.2} />
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── AI ANALYSIS (바로 아래) ───────────────────────── */}
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
            <div className="flex items-center gap-2 mb-2">
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
            <p className="text-base leading-relaxed" style={{ color: "#e2e8f0" }}>
              {data.explanation}
            </p>
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
                {data.rank_pr.toFixed(1)}%
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
                {(50 + data.rank_wr).toFixed(1)}%
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
            {data.vct_act ? (
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
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: "#64748b" }}>PICK RATE</div>
              <div
                className="text-2xl font-black"
                style={{ color: data.vct_pr >= 30 ? "#FF4655" : data.vct_pr >= 10 ? "#e2e8f0" : "#64748B" }}
              >
                {data.vct_pr.toFixed(1)}%
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
                {data.vct_pr < 5 ? "—" : `${data.vct_wr.toFixed(1)}%`}
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
