"use client";

/**
 * 백테스트 전체 예측 테이블 + 필터/검색/접기.
 *
 * 기본 동작:
 *  - 초기에는 상위 20행만 보여주고 "전체 보기" 버튼으로 펼침
 *  - 필터가 적용되면 자동으로 펼쳐짐 (필터의 의미는 "이것만 보여줘")
 */

import { useMemo, useState } from "react";
import type { BacktestPrediction } from "@/lib/backtest";
import type { Locale } from "@/lib/i18n/dict";
import { getDict } from "@/lib/i18n/dict";

const DIR_COLOR: Record<string, string> = {
  stable: "#94A3B8",
  buff: "#4FC3F7",
  nerf: "#FF4655",
};

const LABEL_COLOR: Record<string, string> = {
  stable: "#94A3B8",
  mild_buff: "#7DD3FC",
  strong_buff: "#4FC3F7",
  mild_nerf: "#FCA5A5",
  strong_nerf: "#FF4655",
};

const INITIAL_VISIBLE = 20;

function Chip({ text, color }: { text: string; color: string }) {
  return (
    <span
      className="inline-block text-[11px] px-2 py-0.5 uppercase tracking-wider font-bold whitespace-nowrap"
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
  locale = "ko",
}: {
  rows: BacktestPrediction[];
  acts: string[];
  locale?: Locale;
}) {
  const d = getDict(locale);
  const t = d.predictionTable;
  const verdictLabel = (k: string) => d.verdictLabel[k] ?? k.replace("_", " ");

  const [agentQ, setAgentQ] = useState<string>("");
  const [act, setAct] = useState<string>("ALL");
  const [dir, setDir] = useState<string>("ALL");
  const [hitOnly, setHitOnly] = useState<string>("ALL");
  const [sortByNerf, setSortByNerf] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const hasFilter =
    agentQ.trim().length > 0 ||
    act !== "ALL" ||
    dir !== "ALL" ||
    hitOnly !== "ALL" ||
    sortByNerf;

  const filtered = useMemo(() => {
    let r = rows;
    const q = agentQ.trim().toLowerCase();
    if (q) r = r.filter((x) => x.agent.toLowerCase().includes(q));
    if (act !== "ALL") r = r.filter((x) => x.act === act);
    if (dir !== "ALL") r = r.filter((x) => x.dirPred === dir);
    if (hitOnly === "HIT") r = r.filter((x) => x.hitDir);
    if (hitOnly === "MISS") r = r.filter((x) => !x.hitDir);

    const sorted = [...r];
    if (sortByNerf) {
      sorted.sort((a, b) => b.pNerfDir - a.pNerfDir);
    } else {
      sorted.sort((a, b) => a.actIdx - b.actIdx || b.pNerfDir - a.pNerfDir);
    }
    return sorted;
  }, [rows, agentQ, act, dir, hitOnly, sortByNerf]);

  const showAll = expanded || hasFilter;
  const visible = showAll ? filtered : filtered.slice(0, INITIAL_VISIBLE);

  const reset = () => {
    setAgentQ("");
    setAct("ALL");
    setDir("ALL");
    setHitOnly("ALL");
    setSortByNerf(false);
  };

  return (
    <div className="space-y-4">
      {/* ── 필터 바 ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 text-[13px]">
        <label className="flex items-center gap-2">
          <span
            className="uppercase tracking-widest text-[11px] font-bold"
            style={{ color: "rgba(148,163,184,0.9)" }}
          >
            {t.agentSearchLabel}
          </span>
          <input
            type="text"
            value={agentQ}
            onChange={(e) => setAgentQ(e.target.value)}
            placeholder="Jett, Sage..."
            className="px-3 py-1.5 text-[13px] font-mono outline-none w-36 sm:w-44"
            style={{
              border: "1px solid rgba(51,65,85,0.7)",
              background: "rgba(13,18,32,0.7)",
              color: "#cbd5e1",
            }}
          />
        </label>

        <FilterSelect
          label={t.actLabel}
          value={act}
          onChange={setAct}
          options={[{ v: "ALL", l: t.filterAll }, ...acts.map((a) => ({ v: a, l: a }))]}
        />
        <FilterSelect
          label={t.predLabel}
          value={dir}
          onChange={setDir}
          options={[
            { v: "ALL", l: t.filterAll },
            { v: "stable", l: "stable" },
            { v: "buff", l: "buff" },
            { v: "nerf", l: "nerf" },
          ]}
        />
        <FilterSelect
          label={t.hitLabel}
          value={hitOnly}
          onChange={setHitOnly}
          options={[
            { v: "ALL", l: t.filterAll },
            { v: "HIT", l: t.filterHit },
            { v: "MISS", l: t.filterMiss },
          ]}
        />
        <button
          onClick={() => setSortByNerf((v) => !v)}
          className="px-3 py-1.5 uppercase tracking-widest text-[11px] font-bold transition-colors"
          style={{
            border: sortByNerf ? "1px solid #FF4655" : "1px solid rgba(51,65,85,0.6)",
            color: sortByNerf ? "#FF4655" : "rgba(148,163,184,0.85)",
            background: sortByNerf ? "rgba(255,70,85,0.08)" : "rgba(13,18,32,0.6)",
          }}
        >
          {t.sortToggle}
        </button>
        {hasFilter && (
          <button
            onClick={reset}
            className="px-2.5 py-1.5 uppercase tracking-widest text-[11px] font-bold transition-colors hover:text-white"
            style={{
              border: "1px solid rgba(51,65,85,0.6)",
              color: "rgba(148,163,184,0.85)",
              background: "rgba(13,18,32,0.6)",
            }}
          >
            {t.resetFilter}
          </button>
        )}

        <div className="ml-auto text-[12px]" style={{ color: "rgba(148,163,184,0.9)" }}>
          <span className="font-num font-bold text-[14px]">{filtered.length}</span>
          <span> / </span>
          <span className="font-num">{rows.length}</span>
          <span className="uppercase tracking-widest ml-1">{t.rowsLabel}</span>
        </div>
      </div>

      {/* ── 테이블 ─────────────────────────────────────────────── */}
      <div
        className="overflow-x-auto"
        style={{
          maxHeight: showAll ? "70vh" : "none",
          overflowY: showAll ? "auto" : "visible",
          border: "1px solid rgba(30,41,59,0.8)",
          background: "rgba(13,18,32,0.5)",
        }}
      >
        <table className="w-full text-[13px] tabular-nums" style={{ minWidth: "720px" }}>
          <thead className="sticky top-0 z-10" style={{ background: "rgba(8,12,20,0.95)" }}>
            <tr
              className="uppercase tracking-widest text-[11px] font-bold"
              style={{ color: "rgba(148,163,184,0.9)" }}
            >
              <th className="text-left px-4 py-3">{t.columns.act}</th>
              <th className="text-left px-4 py-3">{t.columns.agent}</th>
              <th className="text-left px-4 py-3">{t.columns.truth}</th>
              <th className="text-left px-4 py-3">{t.columns.predicted}</th>
              <th className="text-right px-4 py-3">p_stable</th>
              <th className="text-right px-4 py-3">p_buff</th>
              <th className="text-right px-4 py-3">p_nerf</th>
              <th className="text-center px-4 py-3">{t.columns.hit}</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r, i) => {
              const rowBg = r.hitDir
                ? `rgba(74,222,128,${i % 2 === 0 ? 0.055 : 0.08})`
                : `rgba(255,70,85,${i % 2 === 0 ? 0.055 : 0.09})`;
              const borderColor = r.hitDir ? "rgba(74,222,128,0.12)" : "rgba(255,70,85,0.14)";
              return (
                <tr
                  key={`${r.agent}-${r.act}`}
                  style={{ background: rowBg, borderTop: `1px solid ${borderColor}` }}
                >
                  <td
                    className="px-4 py-2.5 font-mono whitespace-nowrap"
                    style={{ color: "rgba(203,213,225,0.95)" }}
                  >
                    {r.act}
                  </td>
                  <td
                    className="px-4 py-2.5 font-extrabold tracking-tight whitespace-nowrap"
                    style={{ color: "#e2e8f0" }}
                  >
                    {r.agent}
                  </td>
                  <td className="px-4 py-2.5">
                    <Chip text={verdictLabel(r.truth)} color={LABEL_COLOR[r.truth] ?? "#94A3B8"} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Chip
                      text={verdictLabel(r.predicted)}
                      color={LABEL_COLOR[r.predicted] ?? "#94A3B8"}
                    />
                  </td>
                  <td
                    className="px-4 py-2.5 text-right"
                    style={{ color: "rgba(148,163,184,0.9)" }}
                  >
                    {(r.pStable * 100).toFixed(1)}
                  </td>
                  <td
                    className="px-4 py-2.5 text-right font-bold"
                    style={{ color: DIR_COLOR.buff }}
                  >
                    {(r.pBuffDir * 100).toFixed(1)}
                  </td>
                  <td
                    className="px-4 py-2.5 text-right font-bold"
                    style={{ color: DIR_COLOR.nerf }}
                  >
                    {(r.pNerfDir * 100).toFixed(1)}
                  </td>
                  <td className="px-4 py-2.5 text-center text-xl">
                    {r.hitDir ? (
                      <span
                        className="font-bold"
                        style={{ color: "#4ADE80" }}
                        title={t.hitTooltip}
                      >
                        ✓
                      </span>
                    ) : (
                      <span
                        className="font-bold"
                        style={{ color: "#FF4655" }}
                        title={t.missTooltip}
                      >
                        ✗
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td
                  colSpan={8}
                  className="px-4 py-10 text-center text-[13px]"
                  style={{ color: "rgba(148,163,184,0.75)" }}
                >
                  {t.emptyRows}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── 펼치기 / 접기 버튼 ────────────────────────────────── */}
      {!hasFilter && filtered.length > INITIAL_VISIBLE && (
        <div className="flex justify-center">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="px-5 py-2.5 uppercase tracking-widest text-[12px] font-bold transition-colors"
            style={{
              border: "1px solid rgba(148,163,184,0.4)",
              color: "#e2e8f0",
              background: "rgba(30,41,59,0.5)",
            }}
          >
            {expanded ? t.collapseLabel(INITIAL_VISIBLE) : t.expandLabel(filtered.length)}
          </button>
        </div>
      )}
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
    <label className="flex items-center gap-2">
      <span
        className="uppercase tracking-widest text-[11px] font-bold"
        style={{ color: "rgba(148,163,184,0.9)" }}
      >
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-1.5 text-[13px] font-mono outline-none"
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
