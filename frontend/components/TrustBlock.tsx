import type { BacktestSummary } from "@/lib/backtest";

export default function TrustBlock({ backtest }: { backtest?: BacktestSummary | null }) {
  const hit3 = backtest ? Math.round(backtest.overall.hitRate3 * 100) : null;
  const nActs = backtest?.acts.length ?? null;
  const nSamples = backtest?.totalRows ?? null;

  const items: { label: string; value: string; hint?: string }[] = [
    {
      label: "DATA SOURCE",
      value: "랭크 Diamond+ · VCT · 공식 패치노트",
      hint: "랭크 통계와 대회 데이터를 함께 사용해 패치 압력을 추정합니다.",
    },
    {
      label: "UPDATED",
      value: "자동 갱신 파이프라인 운영",
      hint: "패치, VCT, 학습 산출물 갱신 후 API를 다시 로드합니다.",
    },
    hit3 !== null
      ? {
          label: "MODEL ACCURACY",
          value: `3-class 적중률 ${hit3}% (n=${nSamples})`,
          hint: `walk-forward 백테스트 · ${nActs}개 act 기준`,
        }
      : {
          label: "PROBABILITY",
          value: "확률 점수 기반 우선순위",
          hint: "정답 보장이 아니라 다음 조정 가능성을 비교하는 용도입니다.",
        },
  ];

  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-slate-800/70"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.6)" }}
    >
      {items.map((item) => (
        <div key={item.label} className="p-3.5 sm:p-4">
          <div className="text-[9px] uppercase tracking-[0.25em] mb-1.5" style={{ color: "rgba(148,163,184,0.55)" }}>
            {item.label}
          </div>
          <div className="text-[13px] font-semibold leading-snug" style={{ color: "#e2e8f0" }}>
            {item.value}
          </div>
          {item.hint && (
            <div className="text-[11px] leading-snug mt-1" style={{ color: "rgba(100,116,139,0.85)" }}>
              {item.hint}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
