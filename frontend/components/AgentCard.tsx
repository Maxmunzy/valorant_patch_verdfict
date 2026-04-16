"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import PredBadge from "./PredBadge";
import { AgentPrediction } from "@/lib/api";
import { agentPortrait } from "@/lib/agents";

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
  stable:          "#64748B",
};

function GaugeBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-0.5 relative" style={{ background: "rgba(30,41,59,0.8)" }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(value, 100)}%` }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="absolute inset-y-0 left-0"
        style={{ background: color, boxShadow: `0 0 6px ${color}60` }}
      />
    </div>
  );
}

interface AgentCardProps {
  agent: AgentPrediction;
  size?: "sm" | "lg";
  rank?: number;
}

export default function AgentCard({ agent: a, size = "sm", rank }: AgentCardProps) {
  const accentColor  = VERDICT_COLOR[a.verdict] ?? "#64748B";
  const portrait     = agentPortrait(a.agent);
  const isNerf       = a.verdict.includes("nerf");
  const isBuff       = a.verdict.includes("buff");
  const isRework     = a.verdict === "rework";
  const displayPct   = isNerf ? a.p_nerf : isBuff ? a.p_buff : isRework ? a.p_patch : a.p_patch;
  const justPatched  = a.days_since_patch !== null && a.days_since_patch <= 14 && (a.last_direction === "nerf" || a.last_direction === "buff");

  const href = `/agent/${encodeURIComponent(a.agent)}`;

  /* ── LG card ─────────────────────────────────────── */
  if (size === "lg") {
    return (
      <Link
        href={href}
        className="group relative overflow-hidden block"
        style={{ border: `1px solid ${accentColor}35`, background: "#0d1220" }}
      >
        {/* Portrait */}
        {portrait && (
          <div
            className="absolute top-0 left-0 right-0 pointer-events-none"
            style={{ height: "220px", zIndex: 0 }}
          >
            <Image
              src={portrait}
              alt={a.agent}
              fill
              className="object-cover object-top opacity-20 group-hover:opacity-30 transition-opacity duration-300"
              sizes="340px"
            />
            <div
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(to bottom, transparent 0%, #0d1220 75%), " +
                  "linear-gradient(to right, #0d1220 20%, transparent 60%)",
              }}
            />
          </div>
        )}

        {/* Top accent line */}
        <div
          className="absolute top-0 left-0 right-0 h-px pointer-events-none"
          style={{ zIndex: 5, background: `linear-gradient(90deg, ${accentColor}90, transparent)` }}
        />

        {/* Rank badge */}
        {rank !== undefined && (
          <div
            className="absolute top-3 right-3 text-[10px] font-valo font-black px-1.5 py-0.5 leading-none"
            style={{ zIndex: 15, color: accentColor, border: `1px solid ${accentColor}60`, background: `${accentColor}18` }}
          >
            #{rank}
          </div>
        )}

        {/* 현재 패치 조정됨 배지 */}
        {justPatched && (
          <div
            className="absolute bottom-3 left-4 text-[8px] font-bold px-1.5 py-0.5 uppercase tracking-wider"
            style={{ zIndex: 15, color: "#94a3b8", border: "1px solid rgba(148,163,184,0.25)", background: "rgba(15,23,42,0.85)" }}
          >
            현재 패치 조정됨
          </div>
        )}

        {/* Corner brackets */}
        <div className="absolute top-2.5 left-2.5 w-3 h-3 pointer-events-none" style={{ zIndex: 5, borderTop: `1px solid ${accentColor}55`, borderLeft: `1px solid ${accentColor}55` }} />
        <div className="absolute top-2.5 right-2.5 w-3 h-3 pointer-events-none" style={{ zIndex: 5, borderTop: `1px solid ${accentColor}30`, borderRight: `1px solid ${accentColor}30` }} />

        {/* Header area */}
        <div className="relative p-5 space-y-3" style={{ zIndex: 10, minHeight: "220px" }}>
          <div className="flex justify-between items-start">
            <PredBadge verdict={a.verdict} size="sm" />
            <span className="text-xs uppercase tracking-widest" style={{ color: "rgba(148,163,184,0.75)" }}>
              {a.role}
            </span>
          </div>

          <div className="space-y-2 pt-4">
            <div className="text-5xl font-valo font-black leading-none" style={{ color: accentColor }}>
              {displayPct.toFixed(0)}%
            </div>
            <div className="text-white text-xl font-valo font-bold tracking-tight leading-none mt-1">
              {a.agent}
            </div>
            <div className="text-xs font-num uppercase tracking-wide" style={{ color: "rgba(148,163,184,0.85)" }}>
              RANK {a.rank_pr.toFixed(1)}% PIK · {(50 + a.rank_wr).toFixed(1)}% WR · VCT {a.vct_pr.toFixed(1)}%
            </div>

            <div className="flex items-center gap-2.5 pt-1">
              <span className="text-[10px] uppercase tracking-widest w-12 shrink-0" style={{ color: "rgba(148,163,184,0.7)" }}>
                {isNerf ? "NERF" : isBuff ? "BUFF" : isRework ? "PATCH" : "STBL"}
              </span>
              <div className="flex-1">
                <GaugeBar value={displayPct} color={accentColor} />
              </div>
              <span className="text-[11px] font-num font-bold w-8 text-right" style={{ color: accentColor }}>
                {displayPct.toFixed(0)}%
              </span>
            </div>
          </div>
        </div>

        {/* Hover CTA */}
        <div
          className="absolute bottom-3 right-4 text-[9px] uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          style={{ zIndex: 10, color: accentColor }}
        >
          분석 보기 →
        </div>
      </Link>
    );
  }

  /* ── SM card ─────────────────────────────────────── */
  return (
    <Link
      href={href}
      className="group relative overflow-hidden block"
      style={{ border: `1px solid ${accentColor}30`, background: "#0d1220" }}
    >
      {/* Portrait */}
      {portrait && (
        <div
          className="absolute right-0 top-0 pointer-events-none"
          style={{ width: "45%", height: "100%", zIndex: 0 }}
        >
          <Image
            src={portrait}
            alt={a.agent}
            fill
            className="object-cover object-top opacity-18 group-hover:opacity-28 transition-opacity duration-300"
            sizes="160px"
          />
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(to right, #0d1220 0%, #0d122088 40%, transparent 100%)" }}
          />
        </div>
      )}

      {/* Top glow line */}
      <div
        className="absolute top-0 left-0 right-0 h-px pointer-events-none"
        style={{ zIndex: 5, background: `linear-gradient(90deg, ${accentColor}65, transparent)` }}
      />

      {/* Corner brackets */}
      <div className="absolute top-2 left-2 w-2.5 h-2.5 pointer-events-none" style={{ zIndex: 5, borderTop: `1px solid ${accentColor}50`, borderLeft: `1px solid ${accentColor}50` }} />
      <div className="absolute top-2 right-2 w-2.5 h-2.5 pointer-events-none" style={{ zIndex: 5, borderTop: `1px solid ${accentColor}30`, borderRight: `1px solid ${accentColor}30` }} />

      {/* Main content */}
      <div className="relative p-4 space-y-2.5" style={{ zIndex: 10 }}>
        <div className="flex items-start justify-between">
          <PredBadge verdict={a.verdict} size="sm" />
          <span className="text-[10px] uppercase tracking-widest" style={{ color: "rgba(71,85,105,0.65)" }}>
            {a.role}
          </span>
        </div>

        <div>
          <div className="text-3xl font-valo font-black leading-none" style={{ color: accentColor }}>
            {displayPct.toFixed(0)}%
          </div>
          <div className="text-white text-base font-valo font-bold tracking-tight mt-1">
            {a.agent}
          </div>
          <div className="text-[11px] font-num mt-0.5" style={{ color: "rgba(148,163,184,0.8)" }}>
            {a.rank_pr.toFixed(1)}% PIK · {(50 + a.rank_wr).toFixed(1)}% WR
          </div>
        </div>

        <GaugeBar value={displayPct} color={accentColor} />

        {justPatched && (
          <div
            className="text-[8px] font-bold uppercase tracking-wider mt-1.5"
            style={{ color: "rgba(148,163,184,0.5)", borderTop: "1px solid rgba(51,65,85,0.4)", paddingTop: "6px" }}
          >
            현재 패치 조정됨
          </div>
        )}
      </div>
    </Link>
  );
}
