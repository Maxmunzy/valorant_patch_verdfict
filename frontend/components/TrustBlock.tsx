import type { BacktestSummary } from "@/lib/backtest";

/**
 * 데이터 출처/갱신 시점/확률 의미 + (선택) 모델 실적을 표시하는 신뢰 블록.
 *
 * - 백테스트 데이터가 있으면 적중률/샘플 크기를 같이 보여줘 신뢰도 강화.
 * - 홈 상단에서 ModelAccuracyBanner 와 짝을 이뤄 "숫자 근거"를 노출.
 */
export default function TrustBlock({ backtest }: { backtest?: BacktestSummary | null }) {
  const hit3 = backtest ? Math.round(backtest.overall.hitRate3 * 100) : null;
  const nActs = backtest?.acts.length ?? null;
  const nSamples = backtest?.totalRows ?? null;

  const items: { label: string; value: string; hint?: string }[] = [
    {
      label: "DATA SOURCE",
      value: "랭크 (Diamond+) · VCT 4대륙 공식전",
      hint: "Tracker.gg 랭크 통계 + 리퀴피디아 · Americas · Pacific · EMEA · CN",
    },
    {
      label: "UPDATED",
      value: "매주 자동 갱신",
      hint: "패치 / VCT 액트 단위로 피처 재구축 · 모델 재학습",
    },
    hit3 !== null
      ? {
          label: "MODEL ACCURACY",
          value: `방향성 ${hit3}% 적중 (n=${nSamples})`,
          hint: `walk-forward 백테스트 · ${nActs}개 액트 · 실전 서빙 전 예측만 평가`,
        }
      : {
          label: "PROBABILITY",
          value: "패치 가능성 스코어",
          hint: "실제 확률이 아닌 상대적 위험도 — 높을수록 조정 대상에 가까움",
        },
  ];

  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-slate-800/70"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.6)" }}
    >
      {items.map((it) => (
        <div key={it.label} className="p-3.5 sm:p-4">
          <div
            className="text-[9px] uppercase tracking-[0.25em] mb-1.5"
            style={{ color: "rgba(148,163,184,0.55)" }}
          >
            {it.label}
          </div>
          <div className="text-[13px] font-semibold leading-snug" style={{ color: "#e2e8f0" }}>
            {it.value}
          </div>
          {it.hint && (
            <div className="text-[11px] leading-snug mt-1" style={{ color: "rgba(100,116,139,0.85)" }}>
              {it.hint}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
