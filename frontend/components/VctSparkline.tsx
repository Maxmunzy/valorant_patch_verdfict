/**
 * VCT Sparkline — 카드 위에 표시하는 초소형 PR 추이 그래프.
 *
 * 목적: 상세 페이지 클릭 전에도 "최근 상승세인가 하락세인가" 한눈에.
 * - events.length < 2 면 null 반환 (점 하나로는 추이가 안 생김)
 * - 꺾은선 + 마지막 점만 채움
 * - 뷰박스 기반 · 부모 컨테이너에 맞춰 확장
 */

import type { VctEvent } from "@/lib/api";

interface Props {
  events: VctEvent[];
  accentColor: string;
  /** px — 전체 높이. 기본 22 */
  height?: number;
  /** px — 전체 너비. 기본 90 */
  width?: number;
  /** 이전 대회 대비 상승/하락 배지 텍스트 */
  showTrend?: boolean;
  trendRatio?: number | null;
}

export default function VctSparkline({
  events,
  accentColor,
  height = 22,
  width = 90,
  showTrend = false,
  trendRatio = null,
}: Props) {
  if (!events || events.length < 2) return null;

  // 최근 최대 6개만 스파크라인으로 (너무 빡빡하지 않게)
  const pts = events.slice(-6);
  const n   = pts.length;
  const ys  = pts.map((e) => e.pr);
  const yMax = Math.max(1, ...ys) * 1.1;
  const yMin = 0;

  const padX = 2;
  const padY = 2;
  const innerW = width  - padX * 2;
  const innerH = height - padY * 2;

  const xOf = (i: number) => padX + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
  const yOf = (v: number) => padY + innerH - ((v - yMin) / (yMax - yMin || 1)) * innerH;

  const d = pts.map((e, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(e.pr).toFixed(1)}`).join(" ");
  const lastX = xOf(n - 1);
  const lastY = yOf(ys[n - 1]);

  // 상승/하락 아이콘
  let arrow: { char: string; color: string } | null = null;
  if (showTrend && trendRatio !== null && trendRatio !== undefined) {
    if (trendRatio >= 1.3)      arrow = { char: "↑", color: "#6EE7B7" };
    else if (trendRatio <= 0.7) arrow = { char: "↓", color: "rgba(252,165,165,0.9)" };
  }

  return (
    <span className="inline-flex items-center gap-1 align-middle" title={`최근 ${n}개 대회 PR%`}>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        aria-label="VCT 픽률 추이"
        style={{ display: "block", overflow: "visible" }}
      >
        {/* 베이스라인 (희미) */}
        <line
          x1={padX}
          x2={width - padX}
          y1={height - padY - 0.5}
          y2={height - padY - 0.5}
          stroke="rgba(51,65,85,0.3)"
          strokeWidth={0.5}
        />
        {/* 꺾은선 */}
        <path
          d={d}
          fill="none"
          stroke={accentColor}
          strokeWidth={1.2}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: `drop-shadow(0 0 2px ${accentColor}55)` }}
        />
        {/* 현재 점 */}
        <circle
          cx={lastX}
          cy={lastY}
          r={1.9}
          fill={accentColor}
          stroke={accentColor}
          strokeWidth={1}
        />
      </svg>

      {arrow && (
        <span
          className="text-[10px] font-bold tabular-nums leading-none"
          style={{ color: arrow.color }}
        >
          {arrow.char}
          {trendRatio !== null && trendRatio !== undefined ? trendRatio.toFixed(1) + "×" : ""}
        </span>
      )}
    </span>
  );
}
