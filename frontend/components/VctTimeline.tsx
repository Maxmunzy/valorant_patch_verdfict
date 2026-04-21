"use client";

/**
 * VCT Timeline — 대회별 픽률(PR) 추이를 SVG 꺾은선으로 렌더.
 *
 * - X축: 최근 최대 8개 대회 (과거 → 현재, 좌 → 우)
 * - Y축: PR% (0~max, 10% padding)
 * - 각 점: 호버 시 PR / WR / picks / year 요약
 * - 패치 마커: `last_patch_act_idx` 이상인 첫 이벤트 앞에 세로 점선
 * - 현재(=마지막) 이벤트는 더 크게, 누적(post) 기준선을 옅게 그려 비교
 */

import { useMemo, useState } from "react";
import { VctEventEntry } from "./AgentDetailClient";

interface Props {
  events: VctEventEntry[];
  /** 패치 이후 누적 평균 (옅은 가로 reference line) */
  postAvg?: number;
  /** 마지막 패치 액트 idx — 이 값 이상인 이벤트부터 "패치 이후" */
  lastPatchActIdx?: number | null;
  /** 패치 버전 라벨 (마커 옆 표시) */
  lastPatchVersion?: string | null;
  /** verdict accent color (현재 이벤트 점에 적용) */
  accentColor: string;
}

const PAD_L = 36;
const PAD_R = 16;
const PAD_T = 12;
const PAD_B = 42;
const CHART_H = 200;

function shortName(event: string): string {
  // "Masters Santiago 2026" → "Masters\nSantiago 2026" — 두 줄 허용
  // 짧은 이름은 한 줄.
  if (event.length <= 12) return event;
  const parts = event.split(" ");
  if (parts.length <= 2) return event;
  // 첫 토큰을 헤더로, 나머지를 본문으로
  const mid = Math.ceil(parts.length / 2);
  return parts.slice(0, mid).join(" ") + "\n" + parts.slice(mid).join(" ");
}

export default function VctTimeline({
  events,
  postAvg,
  lastPatchActIdx,
  lastPatchVersion,
  accentColor,
}: Props) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const chart = useMemo(() => {
    if (!events || events.length === 0) return null;
    const ys = events.map((e) => e.pr);
    const yMax = Math.max(1, ...ys, postAvg ?? 0) * 1.15;
    return { yMax };
  }, [events, postAvg]);

  if (!events || events.length === 0 || !chart) {
    return (
      <div
        className="text-center py-6 text-xs"
        style={{ color: "rgba(148,163,184,0.6)", border: "1px dashed rgba(51,65,85,0.5)", background: "rgba(13,18,32,0.3)" }}
      >
        대회 데이터가 부족합니다.
      </div>
    );
  }

  // Responsive width via viewBox. Use fixed logical width for simpler math.
  const W = 600;
  const innerW = W - PAD_L - PAD_R;
  const innerH = CHART_H - PAD_T - PAD_B;

  const n = events.length;
  const xOf = (i: number) =>
    PAD_L + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
  const yOf = (v: number) =>
    PAD_T + innerH - (v / chart.yMax) * innerH;

  // Path for PR line
  const pathD = events
    .map((e, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(e.pr).toFixed(1)}`)
    .join(" ");

  // Y ticks (0, mid, top)
  const ticks = [0, chart.yMax / 2, chart.yMax];

  // 패치 marker: 첫 "post-patch" 이벤트의 인덱스
  const firstPostPatchIdx =
    lastPatchActIdx != null
      ? events.findIndex((e) => e.act_idx >= lastPatchActIdx)
      : -1;
  const patchMarkerX =
    firstPostPatchIdx > 0 ? (xOf(firstPostPatchIdx - 1) + xOf(firstPostPatchIdx)) / 2 : null;

  const hovered = hoverIdx !== null ? events[hoverIdx] : null;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${CHART_H}`}
        className="w-full h-auto block"
        style={{ overflow: "visible" }}
        preserveAspectRatio="none"
      >
        {/* Y 그리드 */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD_L}
              x2={W - PAD_R}
              y1={yOf(t)}
              y2={yOf(t)}
              stroke="rgba(51,65,85,0.35)"
              strokeDasharray={i === 0 ? "none" : "2 3"}
            />
            <text
              x={PAD_L - 6}
              y={yOf(t) + 3}
              fontSize="9"
              textAnchor="end"
              fill="rgba(100,116,139,0.9)"
              fontFamily="monospace"
            >
              {t.toFixed(t < 10 ? 1 : 0)}%
            </text>
          </g>
        ))}

        {/* 누적 평균 reference line */}
        {postAvg !== undefined && postAvg > 0 && postAvg < chart.yMax && (
          <g>
            <line
              x1={PAD_L}
              x2={W - PAD_R}
              y1={yOf(postAvg)}
              y2={yOf(postAvg)}
              stroke="rgba(148,163,184,0.35)"
              strokeDasharray="3 3"
            />
            <text
              x={W - PAD_R - 4}
              y={yOf(postAvg) - 3}
              fontSize="8"
              textAnchor="end"
              fill="rgba(148,163,184,0.7)"
              fontFamily="monospace"
            >
              누적 {postAvg.toFixed(1)}%
            </text>
          </g>
        )}

        {/* 패치 마커 */}
        {patchMarkerX !== null && (
          <g>
            <line
              x1={patchMarkerX}
              x2={patchMarkerX}
              y1={PAD_T}
              y2={PAD_T + innerH}
              stroke="rgba(255,70,85,0.45)"
              strokeDasharray="2 3"
            />
            <text
              x={patchMarkerX + 3}
              y={PAD_T + 10}
              fontSize="9"
              fill="rgba(255,70,85,0.85)"
              fontFamily="monospace"
            >
              {lastPatchVersion ? `${lastPatchVersion} ↓` : "패치 ↓"}
            </text>
          </g>
        )}

        {/* PR 꺾은선 */}
        <path
          d={pathD}
          fill="none"
          stroke={accentColor}
          strokeWidth={1.6}
          strokeLinejoin="round"
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 3px ${accentColor}55)` }}
        />

        {/* 각 이벤트 점 + X축 라벨 + hover zone */}
        {events.map((e, i) => {
          const isLast = i === n - 1;
          const cx = xOf(i);
          const cy = yOf(e.pr);
          const r  = isLast ? 4 : 2.6;
          const label = shortName(e.event);
          const lines = label.split("\n");
          return (
            <g
              key={i}
              onMouseEnter={() => setHoverIdx(i)}
              onMouseLeave={() => setHoverIdx((cur) => (cur === i ? null : cur))}
              style={{ cursor: "pointer" }}
            >
              {/* 큰 hit area for hover */}
              <rect
                x={cx - innerW / (2 * Math.max(n - 1, 1))}
                y={PAD_T}
                width={innerW / Math.max(n - 1, 1)}
                height={innerH}
                fill="transparent"
              />
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={isLast ? accentColor : "#0d1220"}
                stroke={accentColor}
                strokeWidth={isLast ? 2 : 1.3}
              />
              {/* X축 라벨 */}
              {lines.map((ln, li) => (
                <text
                  key={li}
                  x={cx}
                  y={PAD_T + innerH + 14 + li * 10}
                  fontSize="8.5"
                  textAnchor="middle"
                  fill="rgba(148,163,184,0.8)"
                  fontFamily="monospace"
                >
                  {ln}
                </text>
              ))}
              {/* 마지막 포인트에 PR% 직접 표시 */}
              {isLast && (
                <text
                  x={cx}
                  y={cy - 8}
                  fontSize="10"
                  textAnchor="middle"
                  fill={accentColor}
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {e.pr.toFixed(1)}%
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Hover tooltip (absolute positioned, SVG 아래에) */}
      {hovered && (
        <div
          className="absolute top-2 right-2 p-2 text-[10px] font-num leading-tight pointer-events-none"
          style={{
            border: `1px solid ${accentColor}55`,
            background: "rgba(8,12,20,0.92)",
            color: "#e2e8f0",
            minWidth: "140px",
          }}
        >
          <div className="font-bold uppercase tracking-wider mb-1" style={{ color: accentColor }}>
            {hovered.event}
          </div>
          <div className="flex justify-between gap-2">
            <span style={{ color: "rgba(148,163,184,0.85)" }}>PR</span>
            <span>{hovered.pr.toFixed(1)}%</span>
          </div>
          <div className="flex justify-between gap-2">
            <span style={{ color: "rgba(148,163,184,0.85)" }}>WR</span>
            <span>{hovered.picks >= 3 ? `${hovered.wr.toFixed(1)}%` : "—"}</span>
          </div>
          <div className="flex justify-between gap-2">
            <span style={{ color: "rgba(148,163,184,0.85)" }}>PICKS</span>
            <span>{hovered.picks} / {hovered.total_maps} maps</span>
          </div>
        </div>
      )}
    </div>
  );
}
