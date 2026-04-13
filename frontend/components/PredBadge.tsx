"use client";

import { PRED_LABELS } from "@/lib/constants";

const BADGE_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  nerf_rank:       { bg: "rgba(255,70,85,0.1)",   color: "#FF4655", border: "rgba(255,70,85,0.45)" },
  nerf_followup:   { bg: "rgba(255,70,85,0.08)",  color: "#FF4655", border: "rgba(255,70,85,0.35)" },
  nerf_pro:        { bg: "rgba(255,70,85,0.12)",  color: "#FF4655", border: "rgba(255,70,85,0.55)" },
  correction_nerf: { bg: "rgba(249,115,22,0.1)",  color: "#F97316", border: "rgba(249,115,22,0.45)" },
  buff_rank:       { bg: "rgba(79,195,247,0.1)",  color: "#4FC3F7", border: "rgba(79,195,247,0.45)" },
  buff_followup:   { bg: "rgba(79,195,247,0.08)", color: "#4FC3F7", border: "rgba(79,195,247,0.35)" },
  buff_pro:        { bg: "rgba(34,211,238,0.1)",  color: "#22D3EE", border: "rgba(34,211,238,0.45)" },
  correction_buff: { bg: "rgba(129,140,248,0.1)", color: "#818CF8", border: "rgba(129,140,248,0.45)" },
  rework:          { bg: "rgba(167,139,250,0.1)", color: "#A78BFA", border: "rgba(167,139,250,0.45)" },
};

interface PredBadgeProps {
  verdict: string;
  size?: "sm" | "md";
}

export default function PredBadge({ verdict, size = "md" }: PredBadgeProps) {
  const label = PRED_LABELS[verdict];
  const s = BADGE_STYLE[verdict] ?? BADGE_STYLE.buff_followup;
  const text = label ? `${label.icon} ${label.ko}` : verdict;
  const cls = size === "sm" ? "text-[11px] px-2 py-0.5" : "text-xs px-2.5 py-1";

  return (
    <span
      className={`inline-block font-bold uppercase tracking-wide ${cls}`}
      style={{
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        letterSpacing: "0.06em",
      }}
    >
      {text}
    </span>
  );
}
