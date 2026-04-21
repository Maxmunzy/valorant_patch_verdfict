/**
 * 모델 적중률 배너 — 홈 상단 히어로 아래에 배치.
 *
 * walk-forward 백테스트 결과에서 핵심 지표 3개만 뽑아 한 줄로 노출.
 *   - 3-class 적중률 (stable/buff/nerf)
 *   - 고확신 너프 precision (p_nerf >= 0.60)
 *   - Top-3 per-act nerf precision
 *
 * 클릭 시 /backtest 로 이동해 상세 열람.
 */

import Link from "next/link";
import { BacktestSummary } from "@/lib/backtest";

export default function ModelAccuracyBanner({ data }: { data: BacktestSummary | null }) {
  if (!data) return null;

  const hit3   = Math.round(data.overall.hitRate3 * 100);
  const topK   = Math.round(data.topK.nerfPrecisionTop3PerAct * 100);

  // p_nerf >= 0.60 구간 precision
  const highConfNerf = data.highConf.nerf.find((t) => Math.abs(t.threshold - 0.60) < 1e-6);
  const nerfHC = highConfNerf ? Math.round(highConfNerf.precision * 100) : null;

  const first = data.actRange.first;
  const last  = data.actRange.last;
  const nActs = data.acts.length;

  return (
    <Link
      href="/backtest"
      aria-label="백테스트 상세 보기"
      className="block group transition-all hover:brightness-110"
      style={{
        border: "1px solid rgba(74,222,128,0.35)",
        background: "linear-gradient(135deg, rgba(16,185,129,0.08), rgba(74,222,128,0.03))",
      }}
    >
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
        {/* Label */}
        <div className="flex items-center gap-2 shrink-0">
          <div
            className="w-1.5 h-1.5 rotate-45"
            style={{ background: "#4ADE80", boxShadow: "0 0 6px 1px rgba(74,222,128,0.5)" }}
          />
          <span
            className="text-[9px] uppercase tracking-[0.25em] font-valo"
            style={{ color: "rgba(74,222,128,0.9)" }}
          >
            BACKTEST // 최근 {nActs}개 액트
          </span>
        </div>

        {/* Metrics */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 flex-1">
          <Metric
            label="3-class 적중률"
            value={`${hit3}%`}
            hint={`n=${data.totalRows}`}
          />
          {nerfHC !== null && (
            <Metric
              label="고확신 NERF precision"
              value={`${nerfHC}%`}
              hint="p_nerf≥0.60"
            />
          )}
          <Metric
            label="Top-3/액트 NERF precision"
            value={`${topK}%`}
          />
        </div>

        {/* Link arrow */}
        <div
          className="text-[10px] uppercase tracking-widest flex items-center gap-1.5 font-bold ml-auto"
          style={{ color: "rgba(74,222,128,0.85)" }}
        >
          <span className="hidden sm:inline">과거 예측 vs 실제 보기</span>
          <span className="sm:hidden">상세 보기</span>
          <span className="transition-transform group-hover:translate-x-0.5">→</span>
        </div>
      </div>

      {/* 표본 범위 한 줄 */}
      <div
        className="px-4 pb-2 text-[10px] font-mono"
        style={{ color: "rgba(100,116,139,0.65)" }}
      >
        {first} → {last} · walk-forward · 실전 서빙 전 모델이 내린 예측만 평가
      </div>
    </Link>
  );
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span
        className="text-[16px] font-bold font-num tabular-nums"
        style={{ color: "#4ADE80" }}
      >
        {value}
      </span>
      <span
        className="text-[10px] uppercase tracking-wider"
        style={{ color: "rgba(148,163,184,0.75)" }}
      >
        {label}
      </span>
      {hint && (
        <span className="text-[10px]" style={{ color: "rgba(100,116,139,0.7)" }}>
          ({hint})
        </span>
      )}
    </div>
  );
}
