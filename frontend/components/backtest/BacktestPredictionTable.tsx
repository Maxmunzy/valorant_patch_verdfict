"use client";

/**
 * 백테스트 전체 예측 테이블 + 간단 필터/정렬.
 *
 * 표시:
 *  - agent / act / truth / predicted / p_stable · p_buff · p_nerf / 적중 뱃지
 *
 * 필터:
 *  - act 드롭다운 (전체 / 각 act)
 *  - 예측 방향 드롭다운 (전체 / stable / buff / nerf)
 *  - 적중 여부 (전체 / hit / miss)
 *
 * 정렬: act_idx 오름차순 고정 (다시 말해 실제 시간 순).
 *      다만 "p_nerf 높은 순" 토글만 허용 — 너프 예측 강도 중심으로 훑기.
 */

import { useMemo, useState } from "react";
import type { BacktestPrediction } from "@/lib/backtest";

const DIR_COLOR: Record<string, string> = {
  stable: "#94A3B8",
  buff:   "#4FC3F7",
  nerf:   "#FF4655",
};

const LABEL_COLOR: Record<string, string> = {
  stable:      "#94A3B8",
  mild_buff:   "#7DD3FC",
  strong_buff: "#4FC3F7",
  mild_nerf:   "#FCA5A5",
  strong_nerf: "#FF4655",
};

function Chip({ text, color }: { text: string; color: string }) {
  return (
    <span
      className="inline-block text-[9px] px-1.5 py-0.5 uppercase tracking-wider font-bold"
      style={{
        border: `1px solid ${color}55`,
        color: color,
        background: `${color}12`,
      }}
    >
      {text}
    </span>
  );
}

export default function BacktestPredictionTable({
  rows,
  acts,
}: {
  rows: BacktestPrediction[];
  acts: string[];
}) {
  const [act, setAct]         = useState<string>("ALL");
  const [dir, setDir]         = useState<string>("ALL");
  const [hitOnly, setHitOnly] = useState<string>("ALL");
  const [sortByNerf, setSortByNerf] = useState(false);

  const filtered = useMemo(() => {
    let r = rows;
    if (act !== "ALL")  r = r.filter((x) => x.act === act);
    if (dir !== "ALL")  r = r.filter((x) => x.dirPred === dir);
    if (hitOnly === "HIT")  r = r.filter((x) => x.hitDir);
    if (hitOnly === "MISS") r = r.filter((x) => !x.hitDir);

    const sorted = [...r];
    if (sortByNerf) {
      sorted.sort((a, b) => b.pNerfDir - a.pNerfDir);
    } else {
      sorted.sort((a, b) => a.actIdx - b.actIdx || b.pNerfDir - a.pNerfDir);
    }
    return sorted;
  }, [rows, act, dir, hitOnly, sortByNerf]);

  return (
    <div className="space-y-4">
      {/* ── 필터 바 ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 text-[11px]">
        <FilterSelect label="ACT" value={act} onChange={setAct}
          options={[{ v: "ALL", l: "전체" }, ...acts.map((a) => ({ v: a, l: a }))]} />
        <FilterSelect label="예측 방향" value={dir} onChange={setDir}
          options={[
            { v: "ALL", l: "전체" },
            { v: "stable", l: "stable" },
            { v: "buff",   l: "buff" },
            { v: "nerf",   l: "nerf" },
          ]} />
        <FilterSelect label="적중" value={hitOnly} onChange={setHitOnly}
          options={[
            { v: "ALL", l: "전체" },
            { v: "HIT", l: "맞춤" },
            { v: "MISS", l: "틀림" },
          ]} />
        <button
          onClick={() => setSortByNerf((v) => !v)}
          className="px-2.5 py-1 uppercase tracking-widest text-[9px] font-bold transition-colors"
          style={{
            border: sortByNerf ? "1px solid #FF4655" : "1px solid rgba(51,65,85,0.6)",
            color: sortByNerf ? "#FF4655" : "rgba(148,163,184,0.85)",
            background: sortByNerf ? "rgba(255,70,85,0.08)" : "rgba(13,18,32,0.6)",
          }}
        >
          p_nerf 내림차순
        </button>

        <div className="ml-auto text-[10px]" style={{ color: "rgba(100,116,139,0.85)" }}>
          <span className="font-num font-bold">{filtered.length}</span>
          <span> / </span>
          <span className="font-num">{rows.length}</span>
          <span className="uppercase tracking-widest ml-1">rows</span>
        </div>
      </div>

      {/* ── 테이블 ─────────────────────────────────────────────── */}
      <div
        className="overflow-auto"
        style={{
          maxHeight: "70vh",
          border: "1px solid rgba(30,41,59,0.8)",
          background: "rgba(13,18,32,0.5)",
        }}
      >
        <table className="w-full text-[11px] tabular-nums">
          <thead className="sticky top-0 z-10" style={{ background: "rgba(8,12,20,0.95)" }}>
            <tr className="uppercase tracking-widest text-[9px]" style={{ color: "rgba(100,116,139,0.85)" }}>
              <th className="text-left  px-3 py-2">Act</th>
              <th className="text-left  px-3 py-2">Agent</th>
              <th className="text-left  px-3 py-2">Truth</th>
              <th className="text-left  px-3 py-2">Predicted</th>
              <th className="text-right px-3 py-2">p_stable</th>
              <th className="text-right px-3 py-2">p_buff</th>
              <th className="text-right px-3 py-2">p_nerf</th>
              <th className="text-center px-3 py-2">Hit</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => {
              const tc = DIR_COLOR[r.dirTruth] ?? "#94A3B8";
              const pc = DIR_COLOR[r.dirPred]  ?? "#94A3B8";
              const rowBg = i % 2 === 0 ? "rgba(15,20,32,0.4)" : "transparent";
              return (
                <tr key={`${r.agent}-${r.act}`} style={{ background: rowBg, borderTop: "1px solid rgba(30,41,59,0.3)" }}>
                  <td className="px-3 py-1.5 font-mono" style={{ color: "rgba(148,163,184,0.85)" }}>
                    {r.act}
                  </td>
                  <td className="px-3 py-1.5 font-valo uppercase" style={{ color: "#e2e8f0" }}>
                    {r.agent}
                  </td>
                  <td className="px-3 py-1.5">
                    <Chip text={r.truth.replace("_", " ")} color={LABEL_COLOR[r.truth] ?? "#94A3B8"} />
                  </td>
                  <td className="px-3 py-1.5">
                    <Chip text={r.predicted.replace("_", " ")} color={LABEL_COLOR[r.predicted] ?? "#94A3B8"} />
                  </td>
                  <td className="px-3 py-1.5 text-right" style={{ color: "rgba(148,163,184,0.85)" }}>
                    {(r.pStable * 100).toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 text-right" style={{ color: DIR_COLOR.buff }}>
                    {(r.pBuffDir * 100).toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 text-right" style={{ color: DIR_COLOR.nerf }}>
                    {(r.pNerfDir * 100).toFixed(1)}
                  </td>
                  <td className="px-3 py-1.5 text-center">
                    {r.hitDir ? (
                      <span style={{ color: "#4ADE80" }} title="방향성 적중">✓</span>
                    ) : (
                      <span style={{ color: "#FF4655" }} title="오답">✗</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { v: string; l: string }[];
}) {
  return (
    <label className="flex items-center gap-1.5">
      <span className="uppercase tracking-widest text-[9px]" style={{ color: "rgba(100,116,139,0.9)" }}>
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-2 py-1 text-[11px] font-mono outline-none"
        style={{
          border: "1px solid rgba(51,65,85,0.7)",
          background: "rgba(13,18,32,0.7)",
          color: "#cbd5e1",
        }}
      >
        {options.map((o) => (
          <option key={o.v} value={o.v}>
            {o.l}
          </option>
        ))}
      </select>
    </label>
  );
}
